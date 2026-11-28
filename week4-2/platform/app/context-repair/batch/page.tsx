"use client";

import { useEffect, useRef, useState } from "react";
import VisualDiagram, {
  type LinkState,
  type ViewState,
  type VisualCanvasConfig,
  type VisualDiagramHandle,
  type VisualElementProps,
} from "@horsecoder/visual-core";
import styles from "../workflow.module.css";

type Node = { id: string; label: string; x: number; y: number };
type Edge = { from: string; to: string; outcome: string; label: string };
type Definition = { id: string; nodes: Node[]; edges: Edge[] };
type Setup = { definition: Definition; cases: string[] };
type Row = { id: string; before: { passed: number; reached: number };
  native?: { tag: string; invocation: string; nodes: string[] };
  private_local?: { passed: number; tested: number }; fixed_after?: { passed?: number; total?: number; reward?: number };
  public_after?: {exact: boolean}[]; recipe: string | null; trace: [string, string][]; handoffs: number };
type Run = { rows: Row[]; native_registration?: { flow: string } };

function batchUrl(latest = false) {
  const url = new URL("/context-repair/batch/api", window.location.origin);
  if (new URLSearchParams(window.location.search).get("native") === "1") url.searchParams.set("native", "1");
  if (latest) url.searchParams.set("latest", "1");
  return url;
}

function WorkflowNode({ element }: VisualElementProps) {
  return <div className={styles.node} data-stage={element.id}>{element.state.name}</div>;
}

const canvasConfig: VisualCanvasConfig = {
  toolbarConfig: [],
  elementConfig: { components: { stage: { component: WorkflowNode, minSize: { width: 138, height: 42 } } } },
  linkConfig: { components: { transition: { hasArrow: true, showName: true } } },
  globalConfig: { gridSize: 20 },
};

function toView(definition: Definition): ViewState {
  const drawable = definition.nodes.map((node) => ({ ...node, x: node.x + 72 }));
  const byId = new Map(drawable.map((node) => [node.id, node]));
  return {
    id: definition.id,
    elements: drawable.map(({ id, label, x, y }) => ({
      id, name: label, type: "stage", color: "#52777a", x, y, select: false, locked: true,
    })),
    links: definition.edges.map(({ from, to, outcome, label }) => {
      const start = byId.get(from)!;
      const end = byId.get(to)!;
      const horizontal = start.y === end.y;
      const points = horizontal
        ? [{ x: start.x + (start.x < end.x ? 138 : 0), y: start.y + 21 },
           { x: end.x + (start.x < end.x ? 0 : 138), y: end.y + 21 }]
        : [{ x: start.x + 69, y: start.y + 42 },
           { x: start.x + 69, y: end.y - 24 },
           { x: end.x + 69, y: end.y - 24 }, { x: end.x + 69, y: end.y }];
      return { id: `${from}:${outcome}`, name: label, type: "transition", points,
               fromElementId: from, toElementId: to, color: to === "human" ? "#aa5428" : "#52777a" };
    }),
  };
}

export default function ContextRepairPage() {
  const canvas = useRef<VisualDiagramHandle>(null);
  const [setup, setSetup] = useState<Setup | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch(batchUrl(), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw Error("本机编排执行器未就绪");
        return response.json();
      })
      .then(setSetup)
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    fetch(batchUrl(true), { signal: controller.signal })
      .then((response) => response.ok ? response.json() : null)
      .then((previous) => { if (previous?.rows) setRun(previous); })
      .catch(() => {});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (setup) canvas.current?.setView(toView(setup.definition));
  }, [setup]);

  async function execute() {
    const view = canvas.current?.getView();
    if (!view || pending) return;
    setPending(true);
    setError("");
    setRun(null);
    const edges = view.links.map((link: LinkState) => ({
      from: link.fromElementId, to: link.toElementId, outcome: link.id.split(":")[1],
    }));
    try {
      const response = await fetch(batchUrl(), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow: view.id, edges }),
      });
      const result = await response.json();
      if (!response.ok) throw Error(result.error ?? "判题请求未完成");
      setRun(result);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "判题请求未完成");
    } finally {
      setPending(false);
    }
  }

  const nodes = new Map(setup?.definition.nodes.map((node) => [node.id, node.label]));
  return <main className={styles.page}>
    <header className={styles.header}>
      <div>
        <h1>第四周 · 十道失败题的修复对照</h1>
        <p>读取历史固定判分，同输入执行修复前后程序，按代码哈希核验 Linux 复判。</p>
        <a href="?native=1">使用 RSI-Flow 原生诊断与分流</a>
      </div>
      <button type="button" disabled={!setup || pending} onClick={execute}>
        {pending ? "判题中…" : `运行${setup ? ` ${setup.cases.length} 题` : ""}`}
      </button>
    </header>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {pending && <p role="status">正在执行公开样例与反例，并核对修复候选的全量判分。</p>}
    <div className={styles.canvas} aria-label="人工设定的流程画布">
      <VisualDiagram ref={canvas} canvasConfig={canvasConfig} />
    </div>
    {run && <section className={styles.results} aria-label="实测结果">
      <h2>本次判题结果</h2>
      {run.native_registration && <p>已注册流程 <code>{run.native_registration.flow}</code>，引擎返回 {run.rows.filter(r => r.native).length} 条调用回执。</p>}
      <p role="status">共 {run.rows.length} 题，公开对照通过 {run.rows.filter(r => r.public_after?.every(c => c.exact)).length} 题，
        Linux 正式修复 {run.rows.filter(r => r.fixed_after?.reward === 1).length} 题，转人工 {run.rows.reduce((n,r) => n+r.handoffs,0)} 题。</p>
      <table>
        <thead><tr><th>题号</th><th>原固定判分</th><th>本地隐藏组复测</th><th>Linux 复判</th><th>轨迹</th></tr></thead>
        <tbody>{run.rows.map((row) => <tr key={row.id}>
          <th scope="row">{row.id}</th><td>{row.before.passed}/{row.before.reached}，失败即停</td>
          <td>{row.private_local ? row.private_local.passed + "/" + row.private_local.tested : "未运行"}</td>
          <td>{row.fixed_after ? ((row.fixed_after.reward === 1 ? "通过 " : "未通过 ") + (row.fixed_after.passed ?? 0) + "/" + (row.fixed_after.total ?? 0)) : "等待复判"}</td>
          <td><details><summary>{row.recipe ?? "待人工诊断"}</summary>{row.trace.map(([node]) => nodes.get(node)).join(" → ")}
            {row.native && <p>{row.native.nodes.join(" → ")}<br/>{row.native.tag}<br/>调用号 {row.native.invocation}</p>}</details></td>
        </tr>)}</tbody>
      </table>
    </section>}
  </main>;
}

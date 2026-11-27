"use client";

import { useEffect, useRef, useState } from "react";
import VisualDiagram, {
  type LinkState,
  type ViewState,
  type VisualCanvasConfig,
  type VisualDiagramHandle,
  type VisualElementProps,
} from "@horsecoder/visual-core";
import styles from "./workflow.module.css";

type Node = { id: string; label: string; x: number; y: number };
type Edge = { from: string; to: string; outcome: string; label: string };
type Definition = { id: string; nodes: Node[]; edges: Edge[] };
type Setup = { definition: Definition; cases: string[] };
type Score = { status: "pass" | "fail" | "error"; passed?: number; groups_reached?: number; error_code?: number };
type Row = {
  id: string; before: Score; after: Score | null; attempts: number; handoffs: number;
  reason: string | null; experience: string | null;
  trace: { node: string; outcome: string }[];
};
type Run = { cases: number; before_pass: number; before_fail: number; verified_repairs: number;
  human_handoffs: number; automatic_attempts: number; results: Row[] };

const reasons: Record<string, string> = {
  statement_judge_tolerance_conflict: "原题容差与固定判题口径冲突",
  no_match_with_concrete_public_fix: "公开样例没有定位到匹配经验及具体改法",
  failed_after_one_repair: "修订一次后仍未通过",
  judge_infrastructure_error: "判题运行异常",
};

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

function showScore(score: Score | null) {
  if (!score) return "未产生修订判分";
  if (score.status === "error") return "判题异常";
  const verdict = score.status === "pass" ? "通过" : score.error_code === -3 ? "超时" : "未通过";
  return `${verdict} ${score.passed}/${score.groups_reached} 组`;
}

export default function ContextRepairPage() {
  const canvas = useRef<VisualDiagramHandle>(null);
  const [setup, setSetup] = useState<Setup | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/context-runner/workflow", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw Error("本机编排执行器未就绪");
        return response.json();
      })
      .then(setSetup)
      .catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
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
      const response = await fetch("/context-runner/run", {
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
        <h1>EvoAgentBench 人工经验编排</h1>
        <p>用同一批候选代码运行固定判题，最多自动修订一次。</p>
      </div>
      <button type="button" disabled={!setup || pending} onClick={execute}>
        {pending ? "判题中…" : `运行${setup ? ` ${setup.cases.length} 题` : ""}`}
      </button>
    </header>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {pending && <p role="status">正在运行原判题器和公开样例，请保留此页面。</p>}
    <div className={styles.canvas} aria-label="人工设定的流程画布">
      <VisualDiagram ref={canvas} canvasConfig={canvasConfig} />
    </div>
    {run && <section className={styles.results} aria-label="实测结果">
      <h2>本次判题结果</h2>
      <p role="status">共 {run.cases} 题，基线通过 {run.before_pass}，基线失败 {run.before_fail}，
        证实修复 {run.verified_repairs}，自动修订 {run.automatic_attempts}，转人工 {run.human_handoffs}。</p>
      <table>
        <thead><tr><th>题目</th><th>修订前</th><th>结束判分</th><th>执行记录</th></tr></thead>
        <tbody>{run.results.map((row) => <tr key={row.id}>
          <th scope="row">{row.id}</th><td>{showScore(row.before)}</td><td>{showScore(row.after)}</td>
          <td>{row.reason ? reasons[row.reason] : "保留首次判分"}
            <details><summary>节点轨迹</summary>{row.trace.map((step) => nodes.get(step.node)).join(" → ")}</details>
          </td>
        </tr>)}</tbody>
      </table>
    </section>}
  </main>;
}

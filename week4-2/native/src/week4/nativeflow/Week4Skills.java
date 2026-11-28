package week4.nativeflow;

import cc.eamon.open.flow.core.FlowEngine;
import cc.eamon.open.flow.core.stereotype.Flow;
import cc.eamon.open.flow.spring.FlowComponent;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.time.Instant;
import java.util.UUID;

@FlowComponent
public class Week4Skills {
    static final String FLOW = "@week4.evoagentbench/FAILURE_DIAGNOSIS";
    static final String DIAGNOSE = "WEEK4_DIAGNOSE";
    static final String ROUTE = "WEEK4_ROUTE";
    private final ObjectMapper mapper = new ObjectMapper();

    @Flow(DIAGNOSE)
    public void diagnose(String observations) throws IOException {
        JsonNode input = mapper.readTree(observations);
        boolean executionFailure = false, anyMismatch = false, publicMismatch = false, outsideTolerance = false;
        if (!input.path("public").isArray() || !input.path("probes").isArray() || !input.path("task").isTextual())
            throw new IllegalArgumentException("Expected task, public and probes");
        for (String group : new String[]{"public", "probes"}) {
            for (JsonNode observation : input.get(group)) {
                if (!observation.path("exact").isBoolean() || !observation.path("statement").isBoolean()
                        || !observation.path("execution").isTextual()) throw new IllegalArgumentException("Invalid observation");
                executionFailure |= !"ok".equals(observation.get("execution").asText());
                if (!observation.get("exact").booleanValue()) {
                    anyMismatch = true;
                    publicMismatch |= group.equals("public");
                    outsideTolerance |= !observation.get("statement").booleanValue();
                }
            }
        }
        String tag;
        if (executionFailure) tag = "execution_failure";
        else if (!anyMismatch) tag = "needs_counterexample";
        else if (!outsideTolerance) tag = "numeric_comparator";
        else tag = publicMismatch ? "public_mismatch" : "counterexample";
        ObjectNode note = mapper.createObjectNode();
        note.put("task",input.get("task").asText());
        note.put("tag",tag);
        note.put("invocation",UUID.randomUUID().toString());
        note.put("started",Instant.now().toString());
        note.putArray("nodes").add(DIAGNOSE);
        FlowEngine.instance().register("diagnosis",mapper.writeValueAsString(note));
    }

    @Flow(ROUTE)
    public void route(String diagnosis) throws IOException {
        ObjectNode result = (ObjectNode)mapper.readTree(diagnosis);
        String tag = result.get("tag").asText();
        boolean eligible = !tag.equals("needs_counterexample") && !tag.equals("execution_failure");
        result.put("outcome",eligible ? "eligible" : "handoff");
        result.put("flow",FLOW);
        result.withArray("nodes").add(ROUTE);
        result.put("completed",Instant.now().toString());
        FlowEngine.instance().register("result",mapper.writeValueAsString(result));
    }
}

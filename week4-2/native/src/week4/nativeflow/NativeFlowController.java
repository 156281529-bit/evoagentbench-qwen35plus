package week4.nativeflow;

import cc.eamon.open.flow.core.FlowEngine;
import cc.eamon.open.flow.remote.FlowRequest;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Standalone HTTP adapter for the original RSI-Flow engine. */
@RestController
public class NativeFlowController {
    @PostMapping("/api/engine/flow")
    public Map<String, Object> run(@RequestBody FlowRequest request) throws Exception {
        FlowEngine engine = FlowEngine.instance();
        try {
            if (request.getParams() != null) {
                request.getParams().forEach((key, value) -> engine.register(key, value));
            }
            engine.run(request.getFlowId());
            Map<String, Object> data = new LinkedHashMap<>();
            data.put("value", engine.retrieveFlowResults(request.getFlowId()));
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("result", true);
            response.put("status", 200);
            response.put("data", data);
            return response;
        } finally {
            engine.release();
        }
    }
}

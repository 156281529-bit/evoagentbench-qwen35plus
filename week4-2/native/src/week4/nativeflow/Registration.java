package week4.nativeflow;

import cc.eamon.open.flow.core.context.Initializer;
import cc.eamon.open.flow.core.context.InitializerEnums;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class Registration {
    @GetMapping("/week4/registration")
    public Map<String,Object> registered() {
        Initializer registry = InitializerEnums.DEFAULT.getInitializer();
        Map<String,Object> state = new LinkedHashMap<>();
        state.put("flow",Week4Skills.FLOW);
        state.put("assembled",registry.getFlowHolder(Week4Skills.FLOW) != null);
        for (String name : new String[]{Week4Skills.DIAGNOSE,Week4Skills.ROUTE})
            state.put(name,registry.getFlowCodes().containsKey(name));
        return state;
    }
}

package week4.nativeflow;

import cc.eamon.open.flow.spring.config.FlowAutoConfiguration;
import cc.eamon.open.flow.spring.scanner.FlowScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.http.HttpMessageConvertersAutoConfiguration;
import org.springframework.boot.autoconfigure.jackson.JacksonAutoConfiguration;
import org.springframework.boot.autoconfigure.web.servlet.DispatcherServletAutoConfiguration;
import org.springframework.boot.autoconfigure.web.servlet.ServletWebServerFactoryAutoConfiguration;
import org.springframework.boot.autoconfigure.web.servlet.WebMvcAutoConfiguration;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;

@Configuration
@FlowScan(flowPackages = {"week4.nativeflow"})
@Import({FlowAutoConfiguration.class, Week4Skills.class, Registration.class,
    NativeFlowController.class, JacksonAutoConfiguration.class,
    ServletWebServerFactoryAutoConfiguration.class, DispatcherServletAutoConfiguration.class,
    HttpMessageConvertersAutoConfiguration.class, WebMvcAutoConfiguration.class})
public class NativeApplication {
    public static void main(String[] args) {
        SpringApplication.run(NativeApplication.class, args);
    }
}

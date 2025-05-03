package com.example;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.cloud.endpoint.RefreshEndpoint;
import org.springframework.core.env.Environment;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

@RestController
@RefreshScope
public class ConfigController {

    @Value("${example.greeting1:Default greeting from app}")
    private String greeting1;

    @Autowired
    private AppConfigProperties configProperties;

    @Autowired
    private RefreshEndpoint refreshEndpoint;

    @Autowired
    private Environment env;

    private final RestTemplate restTemplate = new RestTemplate();

    @GetMapping("/config-greeting")
    public List<String> getGreeting() {
        return Arrays.asList(greeting1,configProperties.getGreeting());
    }

    @PostMapping("/change-branch")
    public String changeBranch(@RequestParam String branch) {
        // Set the new config label programmatically
        System.setProperty("spring.cloud.config.label", branch);

        // Run refresh asynchronously so main thread is not blocked
        CompletableFuture.runAsync(() -> {
            refreshEndpoint.refresh();
        });

        return "Branch change to '" + branch + "' initiated. Refresh in background.";
    }

    @GetMapping("/admin/instances")
    public List<String> getAdminInstanceUrls(@RequestParam(defaultValue = "client-app") String appName) {
        String adminUrl = "http://localhost:9000/instances";
        List<Map<String, Object>> instances = restTemplate.getForObject(adminUrl, List.class);

        return instances.stream()
                .map(instance -> (Map<String, Object>) instance.get("registration"))
                .filter(registration -> appName.equalsIgnoreCase((String) registration.get("name")))
                .map(registration -> (String) registration.get("serviceUrl"))
                .collect(Collectors.toList());
    }

}

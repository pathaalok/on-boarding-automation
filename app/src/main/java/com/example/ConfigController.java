package com.example;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.cloud.endpoint.RefreshEndpoint;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestTemplate;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

@RestController
@RefreshScope
public class ConfigController {

    @Value("${example.greeting1:Default greeting from app}")
    private String greeting1;

    @Autowired
    private SorCodeProperties sorCodeProperties;

    @Autowired
    private RulesProperties rulesProperties;

    @Autowired
    private RefreshEndpoint refreshEndpoint;

    @Autowired
    private Environment env;

    private final RestTemplate restTemplate = new RestTemplate();

    @GetMapping("/config")
    public Map getConfig() {
        Map<String, Object> result = new HashMap<>();
        result.put("rules", Map.of(
                "Inv_ref_id_rccRule", rulesProperties.getInv_ref_id_rccRule(),
                "Non_regulated_rccRule", rulesProperties.getNon_regulated_rccRule(),
                "Non_regulated_inv_ref_id_rccRule", rulesProperties.getNon_regulated_inv_ref_id_rccRule()
        ));
        result.put("sorCodes", Map.of(
                "Acct", sorCodeProperties.getAcct(),
                "DEAL", sorCodeProperties.getDEAL()
        ));
        return result;
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

    private static final String PROJECT_DIR = "C:\\Users\\Administrator\\Desktop\\on-boarding-automation\\app";

    @GetMapping("/admin/gradle-task")
    public ResponseEntity<String> runGradleTask(@RequestParam String taskName) {
        try {
            // Run the Gradle task to generate the report
            ProcessBuilder processBuilder = new ProcessBuilder("cmd.exe", "/c", "gradlew.bat", taskName);

            processBuilder.directory(new File(PROJECT_DIR));
            processBuilder.redirectErrorStream(true);

            Process process = processBuilder.start();
            StringBuilder output = new StringBuilder();

            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    output.append(line).append("\n");
                }
            }

            int exitCode = process.waitFor();
            output.append("\nExit code: ").append(exitCode);

            // Check if the Gradle task was successful
            if (exitCode == 0 && output.toString().contains("BUILD SUCCESSFUL")) {
                String reportFilePath = PROJECT_DIR+"/build/reports/tests/test/index.html";
                String content = "";

                // Wait for the report to be fully generated (optional sleep)
                Thread.sleep(3000);

                Path reportPath = Paths.get(reportFilePath);
                if (Files.exists(reportPath)) {
                    // Read the report HTML content
                    content = new String(Files.readAllBytes(reportPath));

                    // Embed the CSS directly into the HTML
                    String cssFilePath = PROJECT_DIR+"/build/reports/tests/test/css/style.css";
                    Path cssPath = Paths.get(cssFilePath);
                    String cssContent = new String(Files.readAllBytes(cssPath));

                    String cssFilePath1 = PROJECT_DIR+"/build/reports/tests/test/css/base-style.css";
                    Path cssPath1 = Paths.get(cssFilePath1);
                    String cssContent1 = new String(Files.readAllBytes(cssPath1));

                    // Embed CSS inside <style> tag in the head section
                    content = content.replace("</head>", "<style>"+ cssContent1 +" " + cssContent + "</style></head>");
                } else {
                    content = "JUnit report not found.";
                }

                return ResponseEntity.ok()
                        .header(HttpHeaders.CONTENT_TYPE, MediaType.TEXT_HTML_VALUE)
                        .body(content);
            } else {
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                        .body("Gradle task failed with exit code " + exitCode);
            }

        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Failed to run Gradle task: " + e.getMessage());
        }
    }



}

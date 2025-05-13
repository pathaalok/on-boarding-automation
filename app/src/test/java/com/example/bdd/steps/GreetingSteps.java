package com.example.bdd.steps;

import io.cucumber.java.en.*;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.ResponseEntity;

import static org.assertj.core.api.Assertions.assertThat;

public class GreetingSteps {

    private final TestRestTemplate restTemplate = new TestRestTemplate();
    private ResponseEntity<String> response;

    @When("the client calls /greet with name {string}")
    public void theClientCallsGreet(String name) {
        response = restTemplate.getForEntity("http://localhost:8081/greet?name=" + name, String.class);
    }

    @Then("the response should contain message {string}")
    public void theResponseShouldContain(String expectedMessage) {
        assertThat(response.getBody()).contains(expectedMessage);
    }
}

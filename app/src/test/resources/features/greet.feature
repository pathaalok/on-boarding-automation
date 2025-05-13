# src/test/resources/features/greet.feature
Feature: Greet API

  Scenario: Greet a user
    When the client calls /greet with name "Alok"
    Then the response should contain message "Hello, Alok!"

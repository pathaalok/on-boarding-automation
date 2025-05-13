package com.example.bdd;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

import static io.cucumber.junit.platform.engine.Constants.*;


import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;
import org.junit.runner.RunWith;

//@Suite
//@IncludeEngines("cucumber")
//@SelectClasspathResource("features")
//@ConfigurationParameter(key = GLUE_PROPERTY_NAME, value = "com.example.bdd.steps")
//@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "pretty, json:build/cucumber-report/cucumber.json, html:build/cucumber-report/cucumber.html")
//@ConfigurationParameter(key = FILTER_TAGS_PROPERTY_NAME, value = "not @Ignore") // run all unless ignored

@RunWith(Cucumber.class)
@CucumberOptions(
        features = "src/test/resources/features",
        glue = "com.example.bdd.steps",
        plugin = {"pretty"}
)
public class CucumberTestSuite {
}

package com.example.bdd;

import com.example.GreetingController;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(GreetingController.class)
class GreetingControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void greet_ShouldReturnGreetingMessage() throws Exception {
        String name = "Alok";

        mockMvc.perform(get("/greet").param("name", name))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Hello, Alok!"));
    }
}

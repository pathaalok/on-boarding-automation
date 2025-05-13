package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/greet")
public class GreetingController {

    @GetMapping
    public GreetingResponse greet(@RequestParam String name) {
        return new GreetingResponse("Hello, " + name + "!");
    }

    record GreetingResponse(String message) {}
}

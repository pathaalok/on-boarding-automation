package com.example;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;

import static org.springframework.security.config.Customizer.withDefaults;

@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/instances").permitAll() // Allow access to /instances without authentication
                        .anyRequest().authenticated() // Secure other endpoints
                )
                .formLogin(withDefaults()) // Enable form login
                .httpBasic(withDefaults()) // Enable HTTP Basic Auth
                .csrf(csrf -> csrf.disable()); // Disable CSRF for simplicity (optional)

        return http.build();
    }
}

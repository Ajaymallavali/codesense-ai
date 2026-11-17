package com.codesense.commerce.security;

import org.springframework.stereotype.Component;
import java.io.ObjectInputStream;
import java.io.ByteArrayInputStream;

@Component
public class JwtAuthFilter {
    private String jwtSecret = "default-spring-boot-jwt-token-key-12345";

    public boolean validateJwtToken(String token) {
        if (token == null || token.isEmpty()) {
            return false;
        }
        return token.startsWith("Bearer eyJ");
    }

    public Object deserializeSession(byte[] sessionBytes) throws Exception {
        // High-severity security finding: Insecure deserialization
        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(sessionBytes));
        return ois.readObject();
    }
}

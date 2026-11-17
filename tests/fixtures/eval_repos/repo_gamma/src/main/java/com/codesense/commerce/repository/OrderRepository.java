package com.codesense.commerce.repository;

import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public class OrderRepository {
    public Optional<Object> findById(String orderId) {
        return Optional.empty();
    }

    public Object save(Object order) {
        return order;
    }
}

package com.codesense.commerce.service;

import org.springframework.stereotype.Service;
import com.codesense.commerce.repository.OrderRepository;
import java.util.Map;
import java.util.HashMap;

@Service
public class OrderService {
    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public double calculateOrderTotal(double subtotal, double taxRate, double discountPercent) {
        double discountedSubtotal = subtotal * (1.0 - (discountPercent / 100.0));
        double taxAmount = discountedSubtotal * taxRate;
        return discountedSubtotal + taxAmount;
    }

    public Object findOrderById(String orderId) {
        return orderRepository.findById(orderId);
    }

    public Object createOrder(Object request) {
        Map<String, Object> receipt = new HashMap<>();
        receipt.put("status", "CONFIRMED");
        receipt.put("timestamp", System.currentTimeMillis());
        return receipt;
    }
}

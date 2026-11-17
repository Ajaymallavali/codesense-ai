package com.codesense.commerce.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.codesense.commerce.service.OrderService;
import java.util.List;

@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{orderId}")
    public ResponseEntity<Object> getOrderById(@PathVariable String orderId) {
        Object order = orderService.findOrderById(orderId);
        if (order == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(order);
    }

    @PostMapping("/checkout")
    public ResponseEntity<Object> processCheckout(@RequestBody Object orderRequest) {
        Object receipt = orderService.createOrder(orderRequest);
        return ResponseEntity.ok(receipt);
    }
}

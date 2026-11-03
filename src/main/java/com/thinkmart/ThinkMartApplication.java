package com.thinkmart;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ThinkMartApplication {
    public static void main(String[] args) throws IOException {
        Files.createDirectories(Path.of(".data"));
        SpringApplication.run(ThinkMartApplication.class, args);
    }
}
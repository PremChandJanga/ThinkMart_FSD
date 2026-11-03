package com.thinkmart;

import java.nio.file.Path;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String root = Path.of(".").toAbsolutePath().normalize().toUri().toString();
        registry.addResourceHandler("/*.html", "/app.js")
            .addResourceLocations(root);
        registry.addResourceHandler("/assets/**", "/styles/**")
            .addResourceLocations(root + "assets/", root + "styles/");
    }
}
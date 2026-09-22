FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src src
RUN mvn -B package -DskipTests
FROM eclipse-temurin:17-jre
WORKDIR /app
RUN mkdir -p /data && chown 10001:10001 /data
COPY --from=build /build/target/inspection-backend-1.0.0.jar app.jar
USER 10001
EXPOSE 8080
ENTRYPOINT ["java","-Djava.awt.headless=true","-jar","app.jar"]

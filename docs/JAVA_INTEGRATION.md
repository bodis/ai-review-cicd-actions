# Java Integration Guide

Complete guide for integrating Java static analysis tools into the AI Code Review pipeline.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Free Open-Source Tools](#free-open-source-tools)
3. [Paid Commercial Tools](#paid-commercial-tools)
4. [Configuration](#configuration)
5. [Pipeline Integration](#pipeline-integration)
6. [Cost Comparison](#cost-comparison)
7. [Recommendations](#recommendations)

---

## Overview

The AI Code Review system supports comprehensive Java analysis through multiple tools, from free open-source options to enterprise-grade commercial solutions.

### Supported Tools Matrix

| Tool | Type | Free/Paid | Pipeline Step | Special Resources |
|------|------|-----------|---------------|-------------------|
| **SpotBugs** | Static Analysis | ✅ Free | ✅ Separate | Minimal |
| **PMD** | Static Analysis | ✅ Free | ✅ Separate | Minimal |
| **Checkstyle** | Code Style | ✅ Free | ✅ Separate | Minimal |
| **Error Prone** | Compile-time | ✅ Free | ⚠️ Compile | Minimal |
| **NullAway** | Null Safety | ✅ Free | ⚠️ Error Prone | Minimal |
| **JaCoCo** | Coverage | ✅ Free | ✅ Test Phase | Minimal |
| **OWASP Dependency-Check** | Security/SCA | ✅ Free | ✅ Separate | ⚠️ 500MB DB |
| **Find Security Bugs** | Security | ✅ Free | ⚠️ SpotBugs | Minimal |
| **ArchUnit** | Architecture | ✅ Free | ⚠️ Test Suite | Minimal |
| **SonarQube Community** | Platform | ✅ Free | ✅ Separate | ⚠️ Server Required |
| **SonarQube Developer** | Platform | 💰 Paid | ✅ Separate | ⚠️ Server Required |
| **SonarQube Enterprise** | Platform | 💰 Paid | ✅ Separate | ⚠️ Server Required |
| **SonarCloud** | Platform (SaaS) | 💰 Paid | ✅ Separate | ✅ SaaS |
| **Qodana Community** | Platform | ✅ Free | ✅ Separate | Docker/CLI |
| **Qodana Ultimate** | Platform | 💰 Paid | ✅ Separate | Docker/CLI |
| **Snyk** | Security/SCA | 💰 Paid | ✅ Separate | ✅ SaaS |
| **Codacy** | Platform (SaaS) | 💰 Paid | ✅ Separate | ✅ SaaS |
| **Klocwork** | Enterprise SAST | 💰 Paid | ✅ Separate | ⚠️ Server Required |

---

## Free Open-Source Tools

### 1. SpotBugs

**Purpose:** Detects bugs in Java bytecode (400+ bug patterns)

**Detects:**
- Null pointer dereferences
- Resource leaks
- Concurrency issues
- Bad practices

**Maven Configuration:**
```xml
<plugin>
    <groupId>com.github.spotbugs</groupId>
    <artifactId>spotbugs-maven-plugin</artifactId>
    <version>4.8.3.0</version>
    <configuration>
        <effort>Max</effort>
        <threshold>Low</threshold>
        <xmlOutput>true</xmlOutput>
    </configuration>
</plugin>
```

**Gradle Configuration:**
```gradle
plugins {
    id 'com.github.spotbugs' version '6.0.7'
}

spotbugs {
    effort = 'max'
    reportLevel = 'low'
}
```

**Run Command:**
```bash
# Maven
mvn spotbugs:spotbugs

# Gradle
gradle spotbugsMain
```

---

### 2. PMD

**Purpose:** Source code analysis for bugs, suboptimal code, and duplication

**Detects:**
- Possible bugs
- Dead code
- Suboptimal code
- Overcomplicated expressions
- Duplicate code (via CPD)

**Maven Configuration:**
```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-pmd-plugin</artifactId>
    <version>3.21.2</version>
    <configuration>
        <rulesets>
            <ruleset>/rulesets/java/quickstart.xml</ruleset>
        </rulesets>
    </configuration>
</plugin>
```

**Gradle Configuration:**
```gradle
plugins {
    id 'pmd'
}

pmd {
    ruleSetFiles = files('config/pmd/ruleset.xml')
    ruleSets = []
}
```

**Run Command:**
```bash
# Maven
mvn pmd:pmd pmd:cpd

# Gradle
gradle pmdMain
```

---

### 3. Checkstyle

**Purpose:** Enforces coding standards and style guidelines

**Checks:**
- Naming conventions
- Code formatting
- Javadoc requirements
- Brace usage
- Import order

**Maven Configuration:**
```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-checkstyle-plugin</artifactId>
    <version>3.3.1</version>
    <configuration>
        <configLocation>google_checks.xml</configLocation>
    </configuration>
</plugin>
```

**Gradle Configuration:**
```gradle
plugins {
    id 'checkstyle'
}

checkstyle {
    toolVersion = '10.12.7'
    configFile = file('config/checkstyle/checkstyle.xml')
}
```

**Run Command:**
```bash
# Maven
mvn checkstyle:checkstyle

# Gradle
gradle checkstyleMain
```

---

### 4. OWASP Dependency-Check

**Purpose:** Identifies known CVE vulnerabilities in dependencies

**Features:**
- Scans project dependencies
- Checks against National Vulnerability Database (NVD)
- Reports CVE vulnerabilities
- Configurable fail thresholds

**Maven Configuration:**
```xml
<plugin>
    <groupId>org.owasp</groupId>
    <artifactId>dependency-check-maven</artifactId>
    <version>9.0.9</version>
    <configuration>
        <format>JSON</format>
        <failBuildOnCVSS>7</failBuildOnCVSS>
        <nvdApiKey>${env.NVD_API_KEY}</nvdApiKey>
    </configuration>
</plugin>
```

**Gradle Configuration:**
```gradle
plugins {
    id 'org.owasp.dependencycheck' version '9.0.9'
}

dependencyCheck {
    formats = ['JSON', 'HTML']
    failBuildOnCVSS = 7
    nvdApiKey = System.getenv('NVD_API_KEY')
}
```

**⚠️ Important Notes:**
- First run downloads ~500MB NVD database
- Get free NVD API key from https://nvd.nist.gov/developers/request-an-api-key
- Without API key, rate-limited to 5 requests per 30 seconds
- With API key: 50 requests per 30 seconds

**Run Command:**
```bash
# Maven
mvn dependency-check:check

# Gradle
gradle dependencyCheckAnalyze
```

---

### 5. JaCoCo

**Purpose:** Measures test coverage

**Features:**
- Line coverage
- Branch coverage
- Coverage reports (HTML, XML, CSV)
- Fail builds on low coverage

**Maven Configuration:**
```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.11</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
        <execution>
            <id>check</id>
            <goals>
                <goal>check</goal>
            </goals>
            <configuration>
                <rules>
                    <rule>
                        <element>CLASS</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.80</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

**Run Command:**
```bash
# Maven
mvn clean test jacoco:report

# Gradle
gradle test jacocoTestReport
```

---

### 6. ArchUnit

**Purpose:** Tests architectural rules as unit tests

**Features:**
- Layer dependency rules
- Package structure validation
- Naming conventions enforcement
- Cycle detection

**Example Test:**
```java
@AnalyzeClasses(packages = "com.mycompany")
public class ArchitectureTest {

    @ArchTest
    static final ArchRule layerDependencies = layeredArchitecture()
        .consideringAllDependencies()
        .layer("Controller").definedBy("..controller..")
        .layer("Service").definedBy("..service..")
        .layer("Repository").definedBy("..repository..")
        .whereLayer("Controller").mayNotBeAccessedByAnyLayer()
        .whereLayer("Service").mayOnlyBeAccessedByLayers("Controller")
        .whereLayer("Repository").mayOnlyBeAccessedByLayers("Service");

    @ArchTest
    static final ArchRule servicesShouldNotDependOnControllers =
        noClasses()
            .that().resideInAPackage("..service..")
            .should().dependOnClassesThat().resideInAPackage("..controller..");
}
```

**Dependency:**
```xml
<dependency>
    <groupId>com.tngtech.archunit</groupId>
    <artifactId>archunit-junit5</artifactId>
    <version>1.2.1</version>
    <scope>test</scope>
</dependency>
```

---

### 7. Find Security Bugs

**Purpose:** Security-focused SpotBugs plugin

**Detects:**
- SQL injection
- XSS vulnerabilities
- Cryptography issues
- Insecure configurations
- Command injection

**Maven Configuration:**
```xml
<plugin>
    <groupId>com.github.spotbugs</groupId>
    <artifactId>spotbugs-maven-plugin</artifactId>
    <version>4.8.3.0</version>
    <configuration>
        <plugins>
            <plugin>
                <groupId>com.h3xstream.findsecbugs</groupId>
                <artifactId>findsecbugs-plugin</artifactId>
                <version>1.12.0</version>
            </plugin>
        </plugins>
    </configuration>
</plugin>
```

---

## Paid Commercial Tools

### 1. SonarQube / SonarCloud

**Purpose:** Comprehensive SAST platform

#### SonarQube Community (Free, Self-Hosted)
- 17 languages
- Quality gates
- Security hotspots
- **Requires:** PostgreSQL, 2-4GB RAM

#### SonarQube Developer ($150-5k/year)
- Branch analysis
- PR decoration
- 24 languages
- **Requires:** Server infrastructure

#### SonarQube Enterprise ($20k+/year)
- 29 languages
- Portfolio management
- Advanced security
- **Requires:** Dedicated infrastructure + DBA

#### SonarCloud (SaaS)
- Free for public repos
- €30/month (100k LOC) for private
- No infrastructure needed

**Integration:**
```yaml
# GitHub Actions
- name: SonarCloud Scan
  uses: SonarSource/sonarcloud-github-action@master
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

### 2. Qodana (JetBrains)

**Purpose:** IDE inspections for CI/CD

#### Qodana Community (Free)
- Limited features
- Basic inspections

#### Qodana Ultimate ($58.80/contributor/year)
- Full JetBrains inspections
- 60+ languages
- Quality gates

**Integration:**
```yaml
# GitHub Actions
- name: Qodana Scan
  uses: JetBrains/qodana-action@v2023.3
  with:
    linter: jetbrains/qodana-jvm:latest
```

**Pricing:**
- Minimum 3 contributors
- ~$2,940/year for 50 contributors
- Docker-based, minimal infrastructure

---

### 3. Snyk

**Purpose:** Dependency and code vulnerability scanning

**Features:**
- Dependency vulnerabilities
- Code vulnerabilities
- Container scanning
- IaC scanning
- Fix recommendations

**Pricing:**
- Free: Limited tests/month
- Team: $25/dev/month
- Enterprise: $5k-70k/year

**Integration:**
```yaml
# GitHub Actions
- name: Snyk Security Scan
  uses: snyk/actions/maven@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

---

### 4. Codacy

**Purpose:** Automated code review platform (SaaS)

**Features:**
- Wraps multiple tools (Checkstyle, PMD, SpotBugs)
- Quality gates
- PR decoration
- Coverage tracking

**Pricing:** Contact for pricing (similar to SonarCloud)

---

### 5. Klocwork

**Purpose:** Enterprise-grade SAST

**Features:**
- Differential analysis
- Large codebase support
- Deep static analysis
- Enterprise support

**Pricing:** Enterprise (contact vendor)

---

## Quick Start

### Minimal Setup

Add to your project's workflow (`.github/workflows/code-review.yml`):

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      enable-java-analysis: true
      java-version: '17'
    secrets:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      NVD_API_KEY: ${{ secrets.NVD_API_KEY }}  # Optional but recommended
```

See **[Working Example](../examples/java-workflow-example.yml)** for complete workflow configuration.

---

## Configuration

### Project Configuration Example

For a complete configuration example, see **[`examples/java-spring-boot-config.yml`](../examples/java-spring-boot-config.yml)**.

Basic configuration (`.github/ai-review-config.yml`):

```yaml
project_context:
  name: "Spring Boot Microservice"
  architecture: "Microservices with Spring Boot"
  critical_paths:
    - "src/main/java/com/company/payment/"
    - "src/main/java/com/company/auth/"

# Enable Java analysis
review_aspects:
  - name: java_static_analysis
    enabled: true
    type: classical
    tools:
      - spotbugs
      - pmd
      - checkstyle
      - jacoco
      - owasp-dependency-check
    parallel: true

  # Optional: Add paid tools
  - name: java_sonarcloud
    enabled: true
    type: classical
    tools:
      - sonarcloud
    parallel: false

# Java-specific constraints
project_constraints:
  - "All @RestController methods must have proper @Valid annotations"
  - "Never use java.util.Date - use java.time.* instead"
  - "All database queries must use Spring Data repositories"
  - "Sensitive data must not be logged"

custom_rules:
  - pattern: "java\\.util\\.Date"
    message: "Use java.time.* classes instead of java.util.Date"
    severity: "medium"

  - pattern: "@RequestMapping.*produces.*text/plain"
    message: "Use JSON for API responses, not plain text"
    severity: "low"

blocking_rules:
  block_on_critical: true
  block_on_high: true  # Strict for Spring Boot services
  max_findings:
    critical: 0
    high: 0
    medium: 10
```

---

## Pipeline Integration

### GitHub Actions Workflow

```yaml
name: Java Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  java-analysis:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: maven

      - name: Build project
        run: mvn clean compile

      - name: Run SpotBugs
        run: mvn spotbugs:spotbugs

      - name: Run PMD
        run: mvn pmd:pmd pmd:cpd

      - name: Run Checkstyle
        run: mvn checkstyle:checkstyle

      - name: Run Tests with Coverage
        run: mvn test jacoco:report

      - name: OWASP Dependency Check
        run: mvn dependency-check:check
        env:
          NVD_API_KEY: ${{ secrets.NVD_API_KEY }}

      - name: AI Code Review
        uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
        with:
          enable-java-analysis: true
        secrets:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## Cost Comparison

### Typical Team (50 developers, 1M LOC)

| Solution | Annual Cost | Infrastructure | Setup Effort |
|----------|-------------|----------------|--------------|
| **Open Source Stack** | $0 | Self-managed | Medium |
| **SonarQube Community** | $0 + $1.2-2.4k | VM + PostgreSQL | High |
| **SonarQube Developer** | $5-8k + infra | VM + PostgreSQL | High |
| **SonarQube Enterprise** | $20-30k + infra | Dedicated infra | Very High |
| **SonarCloud Team** | $3.6-15k | None (SaaS) | Low |
| **Qodana Ultimate** | ~$2.9k | Minimal (Docker) | Low |
| **Snyk Team** | ~$15k | None (SaaS) | Low |
| **Codacy** | ~$5-15k | None (SaaS) | Low |

---

## Recommendations

### Small Team (1-10 developers)

**Recommended Stack:**
```yaml
tools:
  - spotbugs
  - pmd
  - checkstyle
  - jacoco
  - owasp-dependency-check
```

**Optional:** SonarCloud Free (for public repos)

**Estimated Cost:** $0/year
**Setup Time:** 2-4 hours

---

### Medium Team (10-50 developers)

**Option 1: Self-Hosted Open Source**
```yaml
tools:
  - spotbugs
  - pmd
  - checkstyle
  - jacoco
  - owasp-dependency-check
  - archunit
  - sonarqube-community  # Self-hosted
```

**Estimated Cost:** $1,200-2,400/year (infrastructure)
**Setup Time:** 1-2 days

**Option 2: SaaS Platform**
```yaml
tools:
  - sonarcloud  # Or Qodana Ultimate
  - snyk-free
```

**Estimated Cost:** $5,000-10,000/year
**Setup Time:** 4-8 hours

---

### Large Team/Enterprise (50+ developers)

**Recommended:**
- **SonarQube Enterprise** or **Qodana Ultimate Plus**
- **Snyk Enterprise** (for advanced dependency security)
- **Full open-source stack** as complementary checks

**Estimated Cost:** $20,000-50,000/year
**Setup Time:** 1-2 weeks

**Benefits:**
- Comprehensive coverage
- Enterprise support
- Advanced security features
- Portfolio management
- Compliance reporting

---

## Maven POM Example

Complete `pom.xml` with all free tools:

```xml
<project>
    <!-- ... -->

    <build>
        <plugins>
            <!-- SpotBugs -->
            <plugin>
                <groupId>com.github.spotbugs</groupId>
                <artifactId>spotbugs-maven-plugin</artifactId>
                <version>4.8.3.0</version>
                <configuration>
                    <effort>Max</effort>
                    <threshold>Low</threshold>
                    <xmlOutput>true</xmlOutput>
                    <plugins>
                        <plugin>
                            <groupId>com.h3xstream.findsecbugs</groupId>
                            <artifactId>findsecbugs-plugin</artifactId>
                            <version>1.12.0</version>
                        </plugin>
                    </plugins>
                </configuration>
            </plugin>

            <!-- PMD -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-pmd-plugin</artifactId>
                <version>3.21.2</version>
                <configuration>
                    <rulesets>
                        <ruleset>/rulesets/java/quickstart.xml</ruleset>
                    </rulesets>
                </configuration>
            </plugin>

            <!-- Checkstyle -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-checkstyle-plugin</artifactId>
                <version>3.3.1</version>
                <configuration>
                    <configLocation>google_checks.xml</configLocation>
                </configuration>
            </plugin>

            <!-- JaCoCo -->
            <plugin>
                <groupId>org.jacoco</groupId>
                <artifactId>jacoco-maven-plugin</artifactId>
                <version>0.8.11</version>
                <executions>
                    <execution>
                        <goals>
                            <goal>prepare-agent</goal>
                        </goals>
                    </execution>
                    <execution>
                        <id>report</id>
                        <phase>test</phase>
                        <goals>
                            <goal>report</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>

            <!-- OWASP Dependency-Check -->
            <plugin>
                <groupId>org.owasp</groupId>
                <artifactId>dependency-check-maven</artifactId>
                <version>9.0.9</version>
                <configuration>
                    <format>JSON</format>
                    <failBuildOnCVSS>7</failBuildOnCVSS>
                </configuration>
            </plugin>
        </plugins>
    </build>

    <dependencies>
        <!-- ArchUnit for Architecture Tests -->
        <dependency>
            <groupId>com.tngtech.archunit</groupId>
            <artifactId>archunit-junit5</artifactId>
            <version>1.2.1</version>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

---

## Troubleshooting

### SpotBugs Issues

**Problem:** Out of memory
```bash
# Solution: Increase heap size
export MAVEN_OPTS="-Xmx2g"
mvn spotbugs:spotbugs
```

### OWASP Dependency-Check Slow

**Problem:** First run takes forever

**Solutions:**
1. Get NVD API key (free): https://nvd.nist.gov/developers/request-an-api-key
2. Use caching:
```yaml
- name: Cache NVD Database
  uses: actions/cache@v3
  with:
    path: ~/.m2/repository/org/owasp/dependency-check-data
    key: ${{ runner.os }}-nvd-${{ hashFiles('**/pom.xml') }}
```

### SonarQube Connection Issues

**Problem:** Cannot connect to SonarQube server

**Solution:** Check firewall and add authentication:
```properties
# sonar-project.properties
sonar.host.url=https://sonarqube.company.com
sonar.login=${SONAR_TOKEN}
```

---

## Next Steps

1. **Start with free tools** - Add SpotBugs, PMD, Checkstyle to your build
2. **Add security scanning** - Enable OWASP Dependency-Check
3. **Measure coverage** - Integrate JaCoCo
4. **Test architecture** - Write ArchUnit tests
5. **Evaluate paid tools** - Try SonarCloud/Qodana for 30 days
6. **Scale gradually** - Add tools based on team growth
7. Review [AI_CONFIGURATION.md](AI_CONFIGURATION.md) for AI-powered review setup
8. Check [examples/java-workflow-example.yml](../examples/java-workflow-example.yml) for complete workflow
9. See main [README.md](../README.md) for overall architecture

---

## Resources

- [SpotBugs Documentation](https://spotbugs.github.io/)
- [PMD Documentation](https://pmd.github.io/)
- [Checkstyle Documentation](https://checkstyle.org/)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)
- [JaCoCo Documentation](https://www.jacoco.org/)
- [ArchUnit User Guide](https://www.archunit.org/)
- [SonarQube Documentation](https://docs.sonarqube.org/)
- [Qodana Documentation](https://www.jetbrains.com/help/qodana/)
- [Snyk Documentation](https://docs.snyk.io/)

---

**Last Updated:** 2024-11
**Version:** 1.0

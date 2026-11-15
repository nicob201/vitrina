plugins {
    id("com.android.application")
}

android {
    namespace = "io.github.nicob201.vitrina"
    compileSdk = 37

    defaultConfig {
        applicationId = "io.github.nicob201.vitrina"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "1.0.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// Framework APIs only: no AndroidX, no third-party libraries (less attack surface).
dependencies {
    testImplementation("junit:junit:4.13.2")
}

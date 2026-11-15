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

    // Release signing is opt-in: only with VITRINA_KEYSTORE set (the key lives outside the repo).
    // Without it, `assembleRelease` makes an unsigned APK and nobody else needs a key.
    val keystore = providers.environmentVariable("VITRINA_KEYSTORE").orNull
    val keystorePassword = providers.environmentVariable("VITRINA_KEYSTORE_PASSWORD").orNull
    if (keystore != null) {
        signingConfigs.create("release") {
            storeFile = file(keystore)
            storePassword = keystorePassword
            keyPassword = keystorePassword // PKCS12 uses one password for both
            keyAlias = "vitrina"
        }
        buildTypes.getByName("release").signingConfig = signingConfigs.getByName("release")
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

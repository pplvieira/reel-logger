import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties().apply {
    if (keystorePropsFile.exists()) {
        keystorePropsFile.inputStream().use { load(it) }
    }
}

android {
    namespace = "dk.sdu.scrolllogger"
    compileSdk = 35

    defaultConfig {
        applicationId = "dk.sdu.scrolllogger"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "LOGGER_VERSION", "\"0.1.0-android\"")
    }

    signingConfigs {
        create("debugFixed") {
            val storeFilePath = keystoreProps.getProperty("storeFile", "debug.keystore")
            storeFile = rootProject.file(storeFilePath)
            storePassword = keystoreProps.getProperty("storePassword", "android")
            keyAlias = keystoreProps.getProperty("keyAlias", "androiddebugkey")
            keyPassword = keystoreProps.getProperty("keyPassword", "android")
        }
    }

    buildTypes {
        debug {
            signingConfig = if (rootProject.file("debug.keystore").exists()) {
                signingConfigs.getByName("debugFixed")
            } else {
                signingConfigs.getByName("debug")
            }
        }
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debugFixed")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        buildConfig = true
        viewBinding = true
    }
    testOptions {
        unitTests.isIncludeAndroidResources = false
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.2.0")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
    testImplementation("com.google.truth:truth:1.4.4")
}

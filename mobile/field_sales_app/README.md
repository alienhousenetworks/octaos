# OctaOS Field Sales & Smart Visit Scheduling Mobile App (Flutter)

A cross-platform Flutter application for real estate field sales specialists and property tour escorts, connecting to the OctaOS backend.

## Core Capabilities
- **My Day Dashboard**: Shows today's sequential property showings, estimated travel times, next visit countdown, and shift status.
- **GPS-Assisted Geofenced Check-In**: Native GPS verification against property site coordinates (250m perimeter) with manual exception logging for cellular deadzones.
- **One-Tap Navigation & Communication**: Handoff to Google Maps / Apple Maps directions and direct customer phone dialer.
- **Autonomous Schedule Recovery**: Real-time push/in-app alert when visit overruns occur, showing schedule diffs and one-tap route acceptance.
- **Offline Event Queue**: Check-ins and visit outcome feedback are queued locally in `SharedPreferences` when offline and automatically synchronized in batch when network connectivity returns.
- **Privacy Controls**: Location collection only occurs during active shift sessions ("On Duty").

---

## Architecture

```
mobile/field_sales_app/
├── lib/
│   ├── main.dart                      # MultiProvider configuration & dark theme
│   ├── constants/
│   │   ├── api_endpoints.dart         # Backend endpoints
│   │   └── theme.dart                 # OctaOS dark-mode palette & typography
│   ├── models/
│   │   ├── visit.dart                 # Field visit & property data model
│   │   ├── agent_status.dart          # Live shift and telemetry model
│   │   ├── recovery_proposal.dart     # AI schedule recovery proposal model
│   │   └── offline_event.dart         # Queued offline event model
│   ├── services/
│   │   ├── api_service.dart           # HTTP client with JWT & tenant headers
│   │   ├── location_service.dart      # Device GPS (Geolocator) & geofencing
│   │   ├── offline_sync_service.dart  # Local queue persistence & batch sync
│   │   └── storage_service.dart       # SharedPreferences key-value store
│   ├── providers/
│   │   ├── auth_provider.dart         # Authentication state & session restore
│   │   └── field_sales_provider.dart  # My Day schedule, check-in, outcome actions
│   └── screens/
│       ├── login_screen.dart          # Tenant credentials & endpoint config
│       ├── my_day_screen.dart         # Shift toggle, next visit hero, itinerary
│       ├── visit_detail_screen.dart   # Buyer info, property specs, delay report
│       ├── check_in_screen.dart       # GPS arrival gauge, manual exception, outcome
│       ├── recovery_screen.dart       # AI schedule recovery diff & accept action
│       └── offline_sync_screen.dart   # Pending offline queue monitor & sync button
└── test/
    ├── geofence_test.dart             # Unit test for Haversine distance math
    └── offline_queue_test.dart        # Unit test for offline event serialization
```

---

## Native Device Permissions

### Android (`android/app/src/main/AndroidManifest.xml`)
```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
    <uses-permission android:name="android.permission.INTERNET" />
</manifest>
```

### iOS (`ios/Runner/Info.plist`)
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>OctaOS requires location access to verify arrival at property site visits and calculate route travel times.</string>
```

---

## Running the App

### Install Dependencies
```bash
flutter pub get
```

### Run Unit Tests
```bash
flutter test
```

### Run on Device or Emulator
```bash
flutter run
```

---

## Server Configuration
By default, the mobile app connects to the OctaOS production server:
* **Production API Base**: `http://151.242.187.221/api/v1`

When configuring the server URL on the login screen, entering the dashboard URL `http://151.242.187.221/app/home` or `http://151.242.187.221` automatically resolves to `http://151.242.187.221/api/v1`.


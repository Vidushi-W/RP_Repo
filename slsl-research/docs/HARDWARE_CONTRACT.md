# Hardware Glove Message Contract (Future)

Physical glove input is not yet connected. When ESP32 hardware details are available, provide:

- Microcontroller model
- Flex / IMU sensor models per finger
- Connection method (USB serial, BLE, Wi-Fi)
- Message format and field order
- Timestamp source (device vs host)
- Nominal sampling rate
- Calibration offsets per glove

## Required adapter interface

All sources must emit `SensorFrame` objects with:

- `timestamp_ms` (float, monotonic per session)
- `features` (22 floats): left flex×5, left acc×3, left gyro×3, right flex×5, right acc×3, right gyro×3

## Transport stubs (not implemented)

- `HardwareSensorSource` — raises until a real adapter is configured
- `HardwareSensorSource.is_available()` — returns `False` until connected

Do not show fake connection indicators. The Playground displays "No device connected" until this contract is fulfilled.

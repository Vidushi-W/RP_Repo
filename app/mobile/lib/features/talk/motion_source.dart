import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';

class MotionInput {
  const MotionInput(this.name, this.bytes);
  final String name;
  final Uint8List bytes;
}

/// Both CSV and the future hardware adapter produce the canonical 23-column CSV.
abstract interface class MotionSource {
  Future<MotionInput?> capture();
}

class CsvMotionSource implements MotionSource {
  @override
  Future<MotionInput?> capture() async {
    final selection = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['csv'],
      withData: true,
    );
    if (selection == null) return null;
    final file = selection.files.single;
    if (file.size > 8 * 1024 * 1024) {
      throw Exception('Choose a CSV smaller than 8 MB.');
    }
    if (file.bytes == null) {
      throw Exception('This recording could not be opened.');
    }
    return MotionInput(file.name, file.bytes!);
  }
}

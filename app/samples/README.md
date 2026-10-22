# Synthetic motion samples

These are unchanged motion-only test recordings from the previous project datasets:
- sample_motion.csv: SLSL_Synthetic_Sentences_v1/tests/test_00001.csv
- sample_angry_motion.csv: SLSL_Angry_Words_Addon_v1/tests/angry_test_00012.csv

They are synthetic research inputs, not validated physical-glove or authentic SLSL
recordings. The client sends no expected words or answer key to the model.
Predictions may differ from the generator's intended labels. Do not add these files
to training if using them to test recognition. Push them to the emulator Downloads
folder with Android Studio or `adb push` and select them with Choose a motion CSV.

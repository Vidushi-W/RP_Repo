"""Optional delivery styles. These presets simulate prosody; they do not detect emotion."""
SPEECH_STYLES = {
    'normal': dict(length_scale=1.0, volume=1.0, noise_scale=.667, noise_w_scale=.8),
    'angry': dict(length_scale=.88, volume=1.12, noise_scale=.72, noise_w_scale=.85),
}

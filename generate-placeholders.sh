#!/bin/bash
# ponytail: native espeak over custom Node TTS script for placeholders.

mkdir -p sounds
cd sounds

declare -A prompts=(
    ["greeting"]="Hello, am I speaking with the correct person?"
    ["identity_confirm"]="Thank you. I am calling from the dealership regarding your enquiry."
    ["explain_enquiry"]="Are you still interested in purchasing?"
    ["ask_model"]="Great! Which model are you looking for?"
    ["ask_location"]="And which city are you located in?"
    ["ask_timeline"]="When are you planning to make the purchase?"
    ["hot"]="Perfect. We have marked you as a hot lead. Our executive will call you. Bye!"
    ["callback"]="No problem. I will call you back later."
    ["postponed"]="Noted. We have postponed your enquiry."
    ["lost"]="Okay, since you already purchased, we will close this."
    ["cold"]="Alright, we have marked you as not interested."
    ["transfer"]="Please hold while I transfer you to a human agent."
    ["rnr"]="No response. Ending call."
)

for state in "${!prompts[@]}"; do
    echo "Generating ${state}.wav..."
    espeak -v en -w "${state}_8k.wav" "${prompts[$state]}"
    # Convert to 8kHz mono 16-bit PCM (FreeSWITCH standard)
    ffmpeg -y -i "${state}_8k.wav" -ar 8000 -ac 1 -acodec pcm_s16le "${state}.wav" >/dev/null 2>&1
    rm "${state}_8k.wav"
done

echo "Placeholders generated in ./sounds/"

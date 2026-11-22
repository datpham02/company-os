#!/usr/bin/env bash
# Tier-1 R&D downloads (Board decisions D2/D3, 2026-11-22). Each file is checked against the SHA256
# published by Hugging Face (LFS oid, read from the API on 2026-11-22) and deleted on mismatch.
set -u
M="$HOME/game-studio-workspace/rnd/models"
HF="https://huggingface.co"
fetch() { # dest url sha256
  local dest="$1" url="$2" want="$3"
  if [ -f "$dest" ] && [ "$(sha256sum "$dest" | cut -c1-64)" = "$want" ]; then echo "OK (present) $dest"; return; fi
  curl -L --fail --retry 3 -s -o "$dest.part" "$url" || { echo "FAIL download $url"; rm -f "$dest.part"; return 1; }
  local got; got=$(sha256sum "$dest.part" | cut -c1-64)
  if [ "$got" = "$want" ]; then mv "$dest.part" "$dest"; echo "OK $dest"; else echo "HASH MISMATCH $dest got $got"; rm -f "$dest.part"; return 1; fi
}
fetch "$M/diffusion_models/flux-2-klein-4b.safetensors" "$HF/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/diffusion_models/flux-2-klein-4b.safetensors" ec3d4e733a771f61c052fb4856c48b336c55eaf2c65487c2a1faeb9bbda7a343
fetch "$M/text_encoders/qwen_3_4b.safetensors" "$HF/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors" 6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a
fetch "$M/vae/flux2-vae.safetensors" "$HF/Comfy-Org/Flux-2-Klein-4B/resolve/main/split_files/vae/flux2-vae.safetensors" 868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3
fetch "$M/background_removal/birefnet.safetensors" "$HF/Comfy-Org/BiRefNet/resolve/main/background_removal/birefnet.safetensors" 9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154
echo "done-core"
fetch "$M/_sources/birefnet_finetuned_toonout.pth" "$HF/joelseytre/toonout/resolve/cbf720eca394edcde66b861a8a8c20fbabe9c748/birefnet_finetuned_toonout.pth" 8c7f8a0bc24400f4caade76622f75ff22ca1e93e169add9d2b70093e2487fbe5
fetch "$M/inpaint/inpaint_v26.fooocus.patch" "$HF/lllyasviel/fooocus_inpaint/resolve/74bbcc070e55219adb9b6c3b0d035b34e3697d1d/inpaint_v26.fooocus.patch" f8657a025104e22d70f9c060635d8e8c2196f433871a2f68dc40abd2171f0d59
fetch "$M/inpaint/fooocus_inpaint_head.pth" "$HF/lllyasviel/fooocus_inpaint/resolve/74bbcc070e55219adb9b6c3b0d035b34e3697d1d/fooocus_inpaint_head.pth" 32f7f838e0c6d8f13437ba8411e77a4688d77a2e34df8857e4ef4d51f6b97692
echo "done-all"

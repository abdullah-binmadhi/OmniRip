class Omnirip < Formula
  include Language::Python::Virtualenv

  desc "P2P-first music acquisition, neural repair, and curation studio TUI"
  homepage "https://github.com/abdullah-binmadhi/OmniRip"
  url "https://github.com/abdullah-binmadhi/OmniRip/archive/refs/tags/v0.1.0.tar.gz"
  license "MIT"
  head "https://github.com/abdullah-binmadhi/OmniRip.git", branch: "main"

  depends_on "python@3.12"
  depends_on "ffmpeg"
  depends_on "chromaprint"

  def install
    virtualenv_install_with_resources
  end

  def caveats
    <<~EOS
      OmniRip is ready! Run `omnirip` to launch the cyber TUI workstation.
      Default AI neural models (Demucs v4, FlashSR) will be auto-downloaded on
      first launch, or you can provision them ahead of time by running:
        omnirip --download-models
    EOS
  end

  test do
    assert_match "OmniRip", shell_output("#{bin}/omnirip --help")
  end
end

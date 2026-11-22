class Omnirip < Formula
  desc "Audiophile Studio System EQ, Mastering Suite & Lossless Music Harvester"
  homepage "https://github.com/abdullah-binmadhi/OmniRip"
  version "0.2.0"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/abdullah-binmadhi/OmniRip/releases/download/v#{version}/omnirip-macos-arm64.tar.gz"
    else
      url "https://github.com/abdullah-binmadhi/OmniRip/releases/download/v#{version}/omnirip-macos-x86_64.tar.gz"
    end
  end

  on_linux do
    if Hardware::CPU.intel?
      url "https://github.com/abdullah-binmadhi/OmniRip/releases/download/v#{version}/omnirip-linux-x86_64.tar.gz"
    end
  end

  depends_on "ffmpeg" => :recommended

  def install
    bin.install "omnirip"
    pkgshare.install "OmniRipAudio.driver" if File.exist?("OmniRipAudio.driver")
  end

  def caveats
    <<~EOS
      Launch OmniRip by running:
        omnirip

      On macOS, the First-Run Setup Wizard will automatically guide you through
      enabling the zero-dot System-Wide Sound Engine via Touch ID / Password
      with no manual terminal sudo required.
    EOS
  end

  test do
    assert_match "omnirip #{version}", shell_output("#{bin}/omnirip --version")
  end
end

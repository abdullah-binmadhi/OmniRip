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
  end

  def caveats
    <<~EOS
      To enable system-wide audio equalization and mastering on macOS,
      install the lightweight CoreAudio HAL driver by opening OmniRip
      and typing :setup (or pressing F12) or executing:
        sudo omnirip driver install
    EOS
  end

  test do
    assert_match "OmniRip", shell_output("#{bin}/omnirip --help")
  end
end

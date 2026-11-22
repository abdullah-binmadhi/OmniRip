class Orchestria < Formula
  desc "Audiophile Studio System EQ, Mastering Suite & Lossless Music Harvester"
  homepage "https://github.com/abdullah-binmadhi/Orchestria"
  version "0.2.0"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/abdullah-binmadhi/Orchestria/releases/download/v#{version}/orchestria-macos-arm64.tar.gz"
    else
      url "https://github.com/abdullah-binmadhi/Orchestria/releases/download/v#{version}/orchestria-macos-x86_64.tar.gz"
    end
  end

  on_linux do
    if Hardware::CPU.intel?
      url "https://github.com/abdullah-binmadhi/Orchestria/releases/download/v#{version}/orchestria-linux-x86_64.tar.gz"
    end
  end

  depends_on "ffmpeg" => :recommended

  def install
    bin.install "orchestria"
    pkgshare.install "OrchestriaAudio.driver" if File.exist?("OrchestriaAudio.driver")
  end

  def caveats
    <<~EOS
      Launch Orchestria by running:
        orchestria

      On macOS, the First-Run Setup Wizard will automatically guide you through
      enabling the zero-dot System-Wide Sound Engine via Touch ID / Password
      with no manual terminal sudo required.
    EOS
  end

  test do
    assert_match "orchestria #{version}", shell_output("#{bin}/orchestria --version")
  end
end

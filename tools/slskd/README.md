# Local slskd setup

`slskd.yml` is a safe template. Do not put real credentials in the tracked
file. Copy it to `slskd.local.yml` and edit the local copy:

```sh
cp tools/slskd/slskd.yml tools/slskd/slskd.local.yml
```

## Credentials

The `credentials` section is the **Soulseek network account**, not an API key.
Use the same Soulseek username and password that work in SoulseekQt. If you
have exposed or shared the password, change it in SoulseekQt first, then put the
new password only in `slskd.local.yml`.

The SoulseekQt listening port (for example `56247`) is unrelated to slskd's
HTTP API port. Leave the slskd web port at `5030`; Harvester is configured to
call `http://localhost:5030` because macOS ControlCenter occupies port 5000 on
the development machine.

## API key

The `web.authentication.api_key` is a local secret that **you create**. It is
not supplied by Soulseek. Generate one with:

```sh
openssl rand -hex 32
```

Put that value in `slskd.local.yml`, and export the same value for Harvester:

```sh
export SLSKD_API_KEY='paste-the-generated-value-here'
export HARVESTER_CONFIG="$PWD/config.toml"
```

Start slskd with the local config:

```sh
cd tools/slskd
./slskd --config slskd.local.yml
```

In another terminal, verify the local API:

```sh
curl -H "X-API-Key: $SLSKD_API_KEY" \
  http://localhost:5030/api/v0/session
```

A `200` response means the local API is reachable. A successful Soulseek
network login is separate: slskd must also report that it is connected to the
Soulseek server. The API can be healthy while the network credentials are
invalid.

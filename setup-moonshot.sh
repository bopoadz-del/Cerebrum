#!/bin/bash
# Setup script for Moonshot AI (Kimi K2.5) with OpenClaw

set -e

echo "🦞 OpenClaw + Kimi K2.5 Setup"
echo "=============================="

# Check if API key is provided
if [ -z "$1" ]; then
    echo ""
    echo "Usage: ./setup-moonshot.sh <YOUR_MOONSHOT_API_KEY>"
    echo ""
    echo "Get your API key from: https://platform.moonshot.ai/console/api-keys"
    exit 1
fi

MOONSHOT_API_KEY="$1"

# Verify key format
if [[ ! "$MOONSHOT_API_KEY" =~ ^sk-[a-zA-Z0-9]+$ ]]; then
    echo "⚠️  Warning: API key doesn't match expected format (should start with 'sk-')"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Step 1: Setting environment variable..."
export MOONSHOT_API_KEY="$MOONSHOT_API_KEY"

# Add to shell profile for persistence
if [ -f ~/.bashrc ]; then
    # Remove old entry if exists
    sed -i '/export MOONSHOT_API_KEY=/d' ~/.bashrc
    echo "export MOONSHOT_API_KEY=\"$MOONSHOT_API_KEY\"" >> ~/.bashrc
    echo "   ✓ Added to ~/.bashrc"
fi

if [ -f ~/.zshrc ]; then
    sed -i '/export MOONSHOT_API_KEY=/d' ~/.zshrc
    echo "export MOONSHOT_API_KEY=\"$MOONSHOT_API_KEY\"" >> ~/.zshrc
    echo "   ✓ Added to ~/.zshrc"
fi

echo ""
echo "Step 2: Updating OpenClaw configuration..."

# Create the updated openclaw.json config
cat > ~/.openclaw/openclaw.json << 'CONFIG'
{
  "gateway": {
    "mode": "local",
    "remote": {
      "url": "ws://127.0.0.1:18789"
    },
    "auth": {
      "mode": "token",
      "token": "a23aa3fbfe72b57eb31c7741cd0eb1c109a8bd52d61cc845"
    },
    "controlUi": {
      "allowedOrigins": [
        "http://localhost:18789",
        "http://127.0.0.1:18789"
      ]
    }
  },
  "env": {
    "MOONSHOT_API_KEY": "REPLACE_WITH_KEY"
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "moonshot/kimi-k2.5"
      },
      "models": {
        "moonshot/kimi-k2.5": {
          "alias": "Kimi K2.5"
        },
        "moonshot/kimi-k2-thinking": {
          "alias": "Kimi K2 Thinking"
        },
        "moonshot/kimi-k2-thinking-turbo": {
          "alias": "Kimi K2 Thinking Turbo"
        },
        "moonshot/kimi-k2-turbo": {
          "alias": "Kimi K2 Turbo"
        }
      }
    }
  },
  "models": {
    "mode": "merge",
    "providers": {
      "moonshot": {
        "baseUrl": "https://api.moonshot.ai/v1",
        "apiKey": "${MOONSHOT_API_KEY}",
        "api": "openai-completions",
        "models": [
          {
            "id": "kimi-k2.5",
            "name": "Kimi K2.5",
            "reasoning": false,
            "input": ["text", "image"],
            "cost": {
              "input": 0,
              "output": 0,
              "cacheRead": 0,
              "cacheWrite": 0
            },
            "contextWindow": 262144,
            "maxTokens": 262144
          },
          {
            "id": "kimi-k2-thinking",
            "name": "Kimi K2 Thinking",
            "reasoning": true,
            "input": ["text"],
            "cost": {
              "input": 0,
              "output": 0,
              "cacheRead": 0,
              "cacheWrite": 0
            },
            "contextWindow": 262144,
            "maxTokens": 262144
          }
        ]
      }
    }
  },
  "wizard": {
    "lastRunAt": "2026-04-11T10:43:34.062Z",
    "lastRunVersion": "2026.4.10",
    "lastRunCommand": "onboard",
    "lastRunMode": "remote"
  },
  "meta": {
    "lastTouchedVersion": "2026.4.10",
    "lastTouchedAt": "2026-04-11T10:43:34.075Z"
  }
}
CONFIG

# Replace the placeholder with actual key
sed -i "s/REPLACE_WITH_KEY/$MOONSHOT_API_KEY/g" ~/.openclaw/openclaw.json

echo "   ✓ Updated ~/.openclaw/openclaw.json"

echo ""
echo "Step 3: Verifying configuration..."
openclaw models list

echo ""
echo "=============================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start the gateway: openclaw gateway run --port 18789"
echo "2. Open TUI: openclaw tui"
echo "3. Or open dashboard: openclaw dashboard"
echo ""
echo "Your OpenClaw is now configured to use Kimi K2.5!"

import pytest
import os
import yaml
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from llm_pii_proxy.security.pii_redaction import PIIRedactionGateway

def test_custom_pattern_from_config(tmp_path):
    # Create a custom config file with a new pattern
    config_path = tmp_path / "pii_patterns.yaml"
    config = {
        "custom_token": [
            {"pattern": r"CUSTOM_[A-Z0-9]{6}"}
        ]
    }
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    # Create gateway with custom config
    gateway = PIIRedactionGateway(str(config_path))
    test_content = "Here is a custom token: CUSTOM_ABC123."
    masked = gateway.mask_sensitive_data(test_content)
    # Should mask the custom token
    assert "CUSTOM_ABC123" not in masked
    assert any("custom_token" in m.type for m in gateway._mapping.values())
    # Unmask should restore
    unmasked = gateway.unmask_sensitive_data(masked)
    assert "CUSTOM_ABC123" in unmasked 
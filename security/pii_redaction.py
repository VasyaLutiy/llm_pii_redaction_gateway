import re
import uuid
import random
from typing import Dict, Tuple, List, Any, Set
from dataclasses import dataclass, field
import os

try:
    import yaml
except ImportError:
    yaml = None

@dataclass
class RedactionMapping:
    original: str
    masked: str
    type: str

class PIIRedactionGateway:
    def __init__(self, config_path: str = "llm_pii_proxy/config/pii_patterns.yaml"):
        """Initialize the gateway with patterns for sensitive data, loaded from config if available"""
        self._mapping: Dict[str, RedactionMapping] = {}
        self.mask_type_map = {
            'aws_access_key': 'aws_key',
            'aws_secret': 'aws_secret',
            'stripe_key': 'api_key',
            'sendgrid_key': 'api_key',
            'jwt_token': 'jwt_token',
            'private_key': 'private_key',
            'password': 'password',
            'connection_string': 'connection_string',
            'ip_address': 'ip_address',
            'api_key': 'api_key'
        }
        self.patterns = {}
        self.priority_patterns = {}
        self.aws_patterns = {}
        self._load_patterns(config_path)

    def _load_patterns(self, config_path: str):
        """Load regex patterns from a YAML config file, fallback to built-in if not found"""
        if yaml is not None and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            for key, entries in config.items():
                self.patterns[key] = [re.compile(e['pattern'], re.MULTILINE | re.DOTALL) for e in entries]
        else:
            # Fallback to built-in patterns (legacy)
            self.patterns = {
                'ip_address': [re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')],
                'password': [re.compile(r'(?i)(?:password|passwd|pwd)[\s:=\"\']+[^\s\"\'\n]+')],
                'api_key': [re.compile(r'(?i)(?:api[_-]?key|access[_-]?key|secret[_-]?key|token)[\s:=\"\']+[^\s\"\'\n]+')],
                'aws_key': [re.compile(r'(AKIA[A-Z0-9]{12,})')],
            }

    def _generate_mask(self, type: str) -> str:
        """Generate a unique mask for sensitive data"""
        # Generate a random 8-character hex string
        random_hex = ''.join(random.choice('0123456789abcdef') for _ in range(8))
        
        # Get the mask type from the mapping
        mask_type = self.mask_type_map.get(type, type)
        return f"<{mask_type}_{random_hex}>"

    def _find_matches(self, text: str, pattern: str) -> List[Tuple[int, int, str]]:
        """Find all non-overlapping matches for a pattern"""
        matches = []
        
        # First try the priority patterns
        if pattern in self.priority_patterns:
            for regex in self.priority_patterns[pattern]:
                for match in regex.finditer(text):
                    value = match.group(0)
                    if ':' in value:
                        label, value = value.split(':', 1)
                        value = value.strip()
                        if not value and '\n' in text[match.end():]:
                            next_line = text[match.end():].split('\n')[1].strip()
                            if next_line:
                                value = next_line
                                match = type('Match', (), {'start': lambda: match.start(), 'end': lambda: match.end() + len(next_line) + 1})

                    # Handle AWS key formats
                    if pattern.startswith('aws_'):
                        value = value.strip('"\'- \t\n\r')
                        if pattern == 'aws_access_key' and 'AKIA' in value:
                            # Try to get from capture group first
                            if len(match.groups()) > 0 and match.group(1):
                                value = match.group(1)
                                # Update match positions to just the captured group
                                start = match.start(1)
                                end = match.end(1)
                                match = type('Match', (), {'start': lambda: start, 'end': lambda: end})
                            else:
                                akia_match = re.search(self.aws_patterns['aws_access_key'], value)
                                if akia_match:
                                    value = akia_match.group(1) if akia_match.groups() else akia_match.group(0)
                                    start = match.start() + value.find(value)
                                    match = type('Match', (), {'start': lambda: start, 'end': lambda: start + len(value)})
                        elif pattern == 'aws_secret' and len(value) >= 20:
                            # Try to get from capture group first
                            if len(match.groups()) > 0 and match.group(1):
                                value = match.group(1)
                                # Update match positions to just the captured group
                                start = match.start(1)
                                end = match.end(1)
                                match = type('Match', (), {'start': lambda: start, 'end': lambda: end})
                            else:
                                secret_match = re.search(self.aws_patterns['aws_secret'], value)
                                if secret_match:
                                    value = secret_match.group(1) if secret_match.groups() else secret_match.group(0)
                                    start = match.start() + value.find(value)
                                    match = type('Match', (), {'start': lambda: start, 'end': lambda: start + len(value)})

                    # Handle password and connection string formats
                    elif pattern in ['password', 'connection_string']:
                        # Try to get the actual value from capture group if available
                        if len(match.groups()) > 0 and match.group(1):
                            value = match.group(1)
                            # Update match positions to just the captured group
                            start = match.start(1)
                            end = match.end(1)
                            match = type('Match', (), {'start': lambda: start, 'end': lambda: end})
                        else:
                            value = value.strip('"\'- \t\n\r')
                            # For connection strings, try to extract the whole URL
                            if pattern == 'connection_string' and '://' in value:
                                url_match = re.search(r'[^\s"\'\n]+://[^\s"\'\n]+', value)
                                if url_match:
                                    value = url_match.group(0)
                                    start = match.start() + value.find(url_match.group(0))
                                    match = type('Match', (), {'start': lambda: start, 'end': lambda: start + len(value)})

                    if not value:
                        continue
                    matches.append((match.start(), match.end(), value))

        # Then try the AWS patterns directly if we're looking for AWS keys
        if pattern.startswith('aws_') and pattern in self.aws_patterns:
            for regex in self.aws_patterns[pattern]:
                for match in regex.finditer(text):
                    value = match.group(0)
                    if not value:
                        continue
                    # Check if this region overlaps with any existing match
                    overlaps = False
                    for start, end, _ in matches:
                        if (match.start() < end and match.end() > start):
                            overlaps = True
                            break
                    if not overlaps:
                        matches.append((match.start(), match.end(), value))

        # Then try the regular patterns if no priority pattern matches were found
        if not matches and pattern in self.patterns:
            for regex in self.patterns[pattern]:
                for match in regex.finditer(text):
                    value = match.group(0)
                    if ':' in value:
                        label, value = value.split(':', 1)
                        value = value.strip()
                        if not value and '\n' in text[match.end():]:
                            next_line = text[match.end():].split('\n')[1].strip()
                            if next_line:
                                value = next_line
                                match = type('Match', (), {'start': lambda: match.start(), 'end': lambda: match.end() + len(next_line) + 1})
                    if not value:
                        continue
                    matches.append((match.start(), match.end(), value))

        # Sort matches by length (longest first) and position
        return sorted(matches, key=lambda x: (-len(x[2]), x[0]))

    def _find_aws_keys(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Find all AWS keys in the text"""
        matches = []
        
        # Find all AKIA keys
        for regex in self.aws_patterns['aws_access_key']:
            for match in regex.finditer(text):
                matches.append((match.start(), match.end(), match.group(0), 'aws_access_key'))
        
        # Find all secret keys
        for regex in self.aws_patterns['aws_secret']:
            for match in regex.finditer(text):
                matches.append((match.start(), match.end(), match.group(0), 'aws_secret'))
        
        # Sort matches by position
        return sorted(matches, key=lambda x: x[0])

    def mask_sensitive_data(self, text: str) -> str:
        """
        Replace sensitive data with masked values
        Returns the masked text
        """
        if not text:
            return text
        
        # Collect all matches from all patterns
        all_matches = []
        
        # Process priority patterns first
        for data_type in self.priority_patterns:
            matches = self._find_matches(text, data_type)
            for start, end, value in matches:
                all_matches.append((start, end, value, data_type))
        
        # Then process regular patterns
        for data_type in self.patterns:
            if data_type in self.priority_patterns:
                continue
            matches = self._find_matches(text, data_type)
            for start, end, value in matches:
                all_matches.append((start, end, value, data_type))
        
        # Remove overlapping matches (keep longer ones)
        filtered_matches = []
        sorted_matches = sorted(all_matches, key=lambda x: (-len(x[2]), x[0]))
        
        for match in sorted_matches:
            start, end, value, data_type = match
            # Check if this match overlaps with any already accepted match
            overlaps = False
            for existing_start, existing_end, _, _ in filtered_matches:
                if start < existing_end and end > existing_start:
                    overlaps = True
                    break
            if not overlaps:
                filtered_matches.append(match)
        
        # Sort matches by position (reverse order to avoid position shifts)
        filtered_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Apply replacements from end to beginning
        masked_text = text
        for start, end, value, data_type in filtered_matches:
            masked = self._generate_mask(data_type)
            self._mapping[masked] = RedactionMapping(
                original=value.strip(),
                masked=masked,
                type=data_type
            )
            masked_text = masked_text[:start] + masked + masked_text[end:]
        
        return masked_text

    def unmask_sensitive_data(self, text: str) -> str:
        """
        Replace masked values with original sensitive data
        Returns the unmasked text
        """
        if not text:
            return text
            
        unmasked_text = text
        
        # Sort masks by length (longest first) to avoid partial replacements
        masks = sorted(self._mapping.keys(), key=len, reverse=True)
        
        for mask in masks:
            if mask in unmasked_text:
                unmasked_text = unmasked_text.replace(mask, self._mapping[mask].original)
        
        return unmasked_text

    def clear_mapping(self):
        """Clear the current mapping of masked values"""
        self._mapping.clear()

# Example usage:
if __name__ == "__main__":
    # Create gateway
    gateway = PIIRedactionGateway()
    
    # Example sensitive text
    sensitive_text = """
    Here's our production config:
    password: super_secret_123
    api_key: sk_live_123456789
    IP Address: 192.168.1.1
    connection_string: Server=myserver;Database=mydb;User Id=sa;Password=mypass;
    mongodb://user:pass@localhost:27017/db
    postgresql://user:pass@localhost:5432/db
    jwt_token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example
    aws_access_key: AKIAIOSFODNN7EXAMPLE
    aws_secret_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    private_key: -----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSj\n-----END PRIVATE KEY-----
    stripe_key: sk_live_51ABC123XYZ456
    sendgrid_key: SG.abcd1234.efgh5678
    """
    
    # Mask sensitive data
    masked_text = gateway.mask_sensitive_data(sensitive_text)
    print("Masked text:")
    print(masked_text)
    
    # Simulate LLM processing
    llm_response = f"Based on your config, I can see you're using {masked_text}"
    
    # Unmask sensitive data in LLM response
    unmasked_response = gateway.unmask_sensitive_data(llm_response)
    print("\nUnmasked response:")
    print(unmasked_response) 
from pydantic import BaseModel, Field, ValidationError
from backend.app.core.logging import get_logger
from backend.app.services.llm_service import llm_service

logger = get_logger(__name__)

class GeneratedRuleSchema(BaseModel):
    title: str = Field(description="A concise, descriptive title for the compliance rule.")
    category: str = Field(description="Must be one of: HR, Security, Finance, Legal, Insurance, GDPR, Internal Policies, Banking, Healthcare, HR-Policy")
    severity: str = Field(description="Must be one of: HIGH, MEDIUM, LOW")
    rule_text: str = Field(description="A precise, clear statement of what is required or prohibited.")
    description: str = Field(description="A short explanation of the context and purpose of the rule.")
    reference: str = Field(description="An industry reference (e.g. SOC2 CC6.1, GDPR Art. 32) or 'Internal Policy'")

class RuleGeneratorService:
    def generate_rule(self, description: str) -> dict:
        """Parse plain-text rule description into a structured compliance rule with retry logic."""
        system_prompt = (
            "You are an expert compliance architect. Your task is to analyze a compliance requirement description "
            "and extract a structured compliance rule in JSON format matching the schema rules.\n"
            "The JSON object must have exactly the following keys:\n"
            "- 'title': string (concise, clear title)\n"
            "- 'category': string (MUST be one of: 'HR', 'Security', 'Finance', 'Legal', 'Insurance', 'GDPR', 'Internal Policies', 'Banking', 'Healthcare', 'HR-Policy')\n"
            "- 'severity': string (MUST be one of: 'HIGH', 'MEDIUM', 'LOW')\n"
            "- 'rule_text': string (the core requirement rule text)\n"
            "- 'description': string (contextual background summary)\n"
            "- 'reference': string (standard control identifier or 'Internal Policy')\n"
        )
        
        user_prompt = (
            f"Please generate a structured rule from the following plain-text requirement:\n\n"
            f"Requirement: \"{description}\"\n\n"
            f"Respond with a valid JSON object."
        )

        max_attempts = 3
        last_error = None
        feedback = ""

        for attempt in range(1, max_attempts + 1):
            try:
                current_user_prompt = user_prompt
                if feedback:
                    current_user_prompt += f"\n\n[WARNING] Previous attempt failed validation:\n{feedback}\nPlease correct these errors and output a valid JSON object."

                llm_result = llm_service.generate_json(
                    system=system_prompt,
                    user=current_user_prompt,
                    required_keys={"title", "category", "severity", "rule_text", "description", "reference"},
                )

                # Validate using Pydantic
                validated = GeneratedRuleSchema(**llm_result)
                
                # Check category constraint
                valid_categories = {'HR', 'Security', 'Finance', 'Legal', 'Insurance', 'GDPR', 'Internal Policies', 'Banking', 'Healthcare', 'HR-Policy'}
                category_normalized = validated.category.strip()
                if category_normalized not in valid_categories:
                    # Fallback to closest or default
                    validated.category = "Internal Policies"

                # Check severity constraint
                valid_severities = {'HIGH', 'MEDIUM', 'LOW'}
                severity_normalized = validated.severity.strip().upper()
                if severity_normalized not in valid_severities:
                    validated.severity = "MEDIUM"
                else:
                    validated.severity = severity_normalized

                return validated.model_dump()

            except (ValidationError, TypeError, ValueError) as exc:
                logger.warning("Attempt %d of rule generation failed validation: %s", attempt, exc)
                last_error = exc
                feedback = str(exc)

        # If all retries failed, raise the final exception
        raise last_error or ValueError("Rule generation failed all attempts due to schema mismatch.")

rule_generator_service = RuleGeneratorService()

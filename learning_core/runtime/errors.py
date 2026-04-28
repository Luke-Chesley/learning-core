class LearningCoreError(RuntimeError): pass


class ConfigurationError(LearningCoreError): pass


class SkillNotFoundError(LearningCoreError): pass


class SkillNotImplementedError(LearningCoreError): pass


class ContractValidationError(LearningCoreError): pass


class ProviderExecutionError(LearningCoreError): pass

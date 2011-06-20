class FixtureUsageError(Exception):
    """
    Raised whenever there's an issue with the way fixture functionality is
    being used, such as invalid items in TestCase.fixtures.
    """
    pass


class RelatedObjectError(Exception):
    """
    Raised for failed relations due to missing dependencies, bad arguments to
    DelayedRelatedObjectLoader resulting in .get() exceptions and other
    cases of relation-related errors.
    """
    pass

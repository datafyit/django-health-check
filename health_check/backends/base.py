import logging

from django.utils.translation import ugettext_lazy as _

logger = logging.getLogger(__name__)


class HealthCheckStatusType(object):
    unavailable = 0
    working = 1
    unexpected_result = 2

HEALTH_CHECK_STATUS_TYPE_TRANSLATOR = {
    0: _("unavailable"),
    1: _("working"),
    2: _("unexpected result"),
}


class HealthCheckException(Exception):
    pass


class ServiceUnavailable(HealthCheckException):
    message = HEALTH_CHECK_STATUS_TYPE_TRANSLATOR[0]
    code = 0


class ServiceReturnedUnexpectedResult(HealthCheckException):
    message = HEALTH_CHECK_STATUS_TYPE_TRANSLATOR[2]
    code = 2


class BaseHealthCheckBackend(object):

    def check_status(self):
        return None

    @property
    def status(self):
        if not getattr(self, "_status", False):
            try:
                setattr(self, "_status", self.check_status())
            except (ServiceUnavailable, ServiceReturnedUnexpectedResult) as e:
                setattr(self, "_status", e.code)

        return self._status

    def pretty_status(self):
        return u"%s" % (HEALTH_CHECK_STATUS_TYPE_TRANSLATOR[self.status])

    @classmethod
    def identifier(cls):
        return cls.__name__


class RetryHealthCheckBackend(BaseHealthCheckBackend):
    """
    Extension of BaseHealthCheckBackend which supports retrying in case of any unexpected Exception

    For this to work, you will need to implement `check_status_implementation` and return check result
    """
    retries = 3

    def check_status_implementation(self):
        raise NotImplementedError("Abstract method.")

    def check_status(self):
        attempts = 0
        while attempts < self.retries:
            try:
                return self.check_status_implementation()
            except (ServiceUnavailable, ServiceReturnedUnexpectedResult) as exc:
                raise exc
            except Exception as e:
                # If check could not be completed, retry it
                logger.warning(e, extra={'attempt': attempts}, exc_info=True)
                attempts += 1

        raise ServiceUnavailable("All retries exhausted.")

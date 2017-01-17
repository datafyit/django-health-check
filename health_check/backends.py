# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.utils.six import text_type
from django.utils.translation import ugettext_lazy as _

from health_check.exceptions import HealthCheckException, ServiceReturnedUnexpectedResult, ServiceUnavailable

logger = logging.getLogger('health-check')


class BaseHealthCheckBackend(object):
    def __init__(self):
        self.errors = []

    def check_status(self):
        raise NotImplementedError

    def run_check(self):
        self.errors = []
        try:
            self.check_status()
        except HealthCheckException as e:
            self.add_error(e, e)
        except BaseException:
            logger.exception("Unexpected Error!")
            raise

    def add_error(self, error, cause=None):
        if isinstance(error, HealthCheckException):
            pass
        elif isinstance(error, text_type):
            msg = error
            error = HealthCheckException(msg)
        else:
            msg = _("unknown error")
            error = HealthCheckException(msg)
        if isinstance(cause, BaseException):
            logger.exception(text_type(error))
        else:
            logger.error(text_type(error))
        self.errors.append(error)

    def pretty_status(self):
        if self.errors:
            return "\n".join(str(e) for e in self.errors)
        return _('working')

    @property
    def status(self):
        return int(not self.errors)

    def identifier(self):
        return self.__class__.__name__


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

        self.add_error(ServiceUnavailable("Could not check status."))

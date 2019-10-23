"""
Provide logic for mapping processing params < = > GUI controls
"""
import logging
from typing import List, Any

from PyQt5.QtWidgets import QWidget, QSlider, QCheckBox, QComboBox

from als.code_utilities import AlsException, log
from als.model.params import ProcessingParameter, RangeParameter, SwitchParameter, ListParameter
from als.ui.widgets import Slider, DEFAULT_SLIDER_MAX

_LOGGER = logging.getLogger(__name__)


class UnsupportedParamMapping(AlsException):
    """Raised when trying to work on incompatible couple param / control"""


class UnknownWidget(AlsException):
    """Raised when trying to get a control's value getter / setters functions"""


@log
def _check_param_control_pairing(param: ProcessingParameter, control: QWidget):
    """

    Raise an exception if we cannot match this param / control pair

    :param param: The parameter to check
    :type param: ProcessingParameter

    :param control: the control to check
    :type control: QWidget

    :raises UnsupportedParamMapping: param/control pair is not supported
    """

    if isinstance(param, RangeParameter) and isinstance(control, QSlider):
        return

    if isinstance(param, SwitchParameter) and isinstance(control, QCheckBox):
        return

    if isinstance(param, ListParameter) and isinstance(control, QComboBox):
        return

    raise UnsupportedParamMapping("Unsupported parameter / control pair",
                                  f"No recipe for couple {type(param)}/{type(control)}")


@log
def _get_control_setter_function(control):
    """
    Gets the function used to set a GUI control's value

    :param control: the control
    :type control: QWidget

    :return: the function used to set the control's value
    """
    if isinstance(control, QSlider):
        return control.setValue

    if isinstance(control, QCheckBox):
        return control.setChecked

    if isinstance(control, QComboBox):
        return control.setCurrentText

    raise UnknownWidget("Could not get setter function", f"We don't know anything about {type(control)}")


@log
def _get_control_getter_function(control):
    """
    Gets the function used to get a GUI control's value

    :param control: the control
    :type control: QWidget

    :return: the function used to get the control's value
    """
    if isinstance(control, QSlider):
        return control.value

    if isinstance(control, QCheckBox):
        return control.isChecked

    if isinstance(control, QComboBox):
        return control.currentText

    raise UnknownWidget("Could not get getter function", f"We don't know anything about {type(control)}")


@log
def _update_control_from_param(param: ProcessingParameter, control: QWidget):
    """

    Generic function to update a GUI control from a processing parameter

    :param param: The source parameter
    :type param: ProcessingParameter

    :param control: the control to update
    :type control: QWidget
    """

    _check_param_control_pairing(param, control)

    getters_dict = {

        RangeParameter: lambda p: _compute_slider_value_from_param_value(p.value, p.maximum - p.minimum),
        SwitchParameter: lambda p: p.value,
        ListParameter: lambda p: p.value,
    }

    # set control value according to param value
    control_value_setter_function = _get_control_setter_function(control)
    param_value_transformation_function = getters_dict[type(param)]

    control_value_setter_function(param_value_transformation_function(param))

    # set control tooltip as param description
    control.setToolTip(param.description)


@log
def _update_param_from_control(param: ProcessingParameter, control: QWidget):
    """

    Generic function to update a processing parameter from a GUI control

    :param param: The destination parameter
    :type param: ProcessingParameter

    :param control: the source control
    :type control: QWidget
    """

    _check_param_control_pairing(param, control)

    value_transformations_dict = {

        # pylint: disable=W0108
        RangeParameter: lambda p, v: _compute_param_value_from_slider_value(p, v),
        SwitchParameter: lambda p, v: v,
        ListParameter: lambda p, v: v,
    }

    # set param value according to control value
    control_value_getter_function = _get_control_getter_function(control)
    param_value_transformation_function = value_transformations_dict[type(param)]

    param.value = param_value_transformation_function(param, control_value_getter_function())

    _LOGGER.debug(f"New value for {param.name} : {param.value}")


@log
def update_params_from_controls(params: List[ProcessingParameter], controls: List[QWidget]):
    """
    Update a list of processing parameters from a matched list of GUI controls

    :param params: the param list
    :type params: List[ProcessingParameter]

    :param controls: the control list
    :type controls: List[QWidget]
    """

    for param, control in zip(params, controls):
        _update_param_from_control(param, control)


@log
def update_controls_from_params(params: List[ProcessingParameter], controls: List[QWidget]):
    """
    Update a list of GUI controls from a matched list of processing parameters

    :param params: the param list
    :type params: List[ProcessingParameter]

    :param controls: the control list
    :type controls: List[QWidget]
    """
    for param, control in zip(params, controls):
        _update_control_from_param(param, control)


@log
def reset_params(params: List[ProcessingParameter], controls: List[QWidget]):
    """
    Reset a list of ProcessingParameter and update associated controls

    :param params: the param list
    :type params: List[ProcessingParameter]

    :param controls: the control list
    :type controls: List[QWidget]
    """

    for param in params:
        param.reset()
        update_controls_from_params(params, controls)


@log
def set_sliders_defaults(params: List[RangeParameter], sliders: List[Slider]):
    """
    Works on matched lists : sets each slider's default value according to matched param default value

    :param params: the parameters
    :type params: List[RangeParameter]

    :param sliders: the sliders
    :type sliders: List[Slider]
    """

    for param, slider in zip(params, sliders):
        slider.set_default_value(_compute_slider_value_from_param_value(param.default, param.maximum - param.minimum))


@log
def _compute_slider_value_from_param_value(value: Any, amplitude: Any):
    """
    Performs mapping from param value space to slider value space

    :param value: the value from param space
    :type value: numeric

    :param amplitude: the param value amplitude, typically p.max - p.min
    :type amplitude: numeric

    :return: mapped value
    :rtype: muneric
    """

    return value / amplitude * DEFAULT_SLIDER_MAX

@log
def _compute_param_value_from_slider_value(param: RangeParameter, slider_value):
    """
    Performs mapping from slider value space to param value space

    :param param: the parameter matched to the slider we got slider_value from
    :type param: RangeParameter

    :param slider_value: the slider value
    :type slider_value: numeric

    :return: mapped value
    :rtype: muneric
    """

    return slider_value / DEFAULT_SLIDER_MAX * (param.maximum - param.minimum)

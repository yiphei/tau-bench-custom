from cashier.graph import NodeSchema, BaseStateModel, EdgeSchema, GraphSchema
from typing import Optional, List, Dict
from tau_bench.agents.custom_tool_call_data.types import (
    FlightInfo,
    PassengerInfo,
    PaymentMethod,
    InsuranceValue,
    UserDetails,
)
from tau_bench.agents.custom_tool_call_data.prompts import AirlineNodeSystemPrompt
from pydantic import Field, BaseModel
from tau_bench.agents.custom_tool_call_data.tool_registry import AIRLINE_TOOL_REGISTRY
from tau_bench.agents.custom_tool_call_data.types import ReservationDetails

## book flight graph

PREAMBLE = "You are helping the customer to change flight/s. "


class UserState(BaseStateModel):
    user_details: Optional[UserDetails] = None


get_user_id_node_schema = NodeSchema(
    node_prompt=PREAMBLE + "Right now, you need to get their user details.",
    node_system_prompt=AirlineNodeSystemPrompt,
    input_pydantic_model=None,
    state_pydantic_model=UserState,
    tool_registry_or_tool_defs=AIRLINE_TOOL_REGISTRY,
    tool_names=["get_user_details", "calculate"],
)

# ---------------------------------------------------------


class UserInput(BaseModel):
    user_details: UserDetails


class ReservationDetails(BaseStateModel):
    reservation_details: Optional[ReservationDetails] = None


get_reservation_details_node_schema = NodeSchema(
    node_prompt=PREAMBLE
    + "Right now, you need to get the reservation details by asking for the reservation id. If they don't know the id, lookup each reservation in their user details and find the one that best matches their description .",
    node_system_prompt=AirlineNodeSystemPrompt,
    input_pydantic_model=UserInput,
    state_pydantic_model=ReservationDetails,
    tool_registry_or_tool_defs=AIRLINE_TOOL_REGISTRY,
    tool_names=[
        "get_reservation_details",
        "calculate",
        "list_all_airports",
    ],
)


# ---------------------------------------------------------


class OrderInput1(BaseModel):
    user_details: UserDetails
    reservation_details: ReservationDetails


class FlightOrder(BaseStateModel):
    flight_infos: List[FlightInfo] = Field(
        default_factory=list,
        descripion="An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.",
    )


find_flight_node_schema = NodeSchema(
    node_prompt=PREAMBLE
    + (
        "Right now, you need to help find new flights for them. The customer can change anything from a single flight segment to all the flights. "
        "Remember, basic economy flights cannot be modified. Other reservations can be modified without changing the origin, destination, and trip type."
    ),
    node_system_prompt=AirlineNodeSystemPrompt,
    input_pydantic_model=OrderInput1,
    state_pydantic_model=FlightOrder,
    tool_registry_or_tool_defs=AIRLINE_TOOL_REGISTRY,
    tool_names=[
        "search_direct_flight",
        "search_onestop_flight",
        "list_all_airports",
        "calculate",
    ],
)


# ------------------------------------------------------------------
class OrderInput2(BaseModel):
    user_details: UserDetails
    reservation_details: ReservationDetails
    flight_infos: List[FlightInfo]


class PaymentOrder(BaseStateModel):
    payment_id: str


get_payment_node_schema = NodeSchema(
    node_prompt=PREAMBLE
    + (
        "Right now, you need to get the payment information. They can only use gift card or credit card "
        "IMPORTANT: All payment methods must already be in user profile for safety reasons."
    ),
    node_system_prompt=AirlineNodeSystemPrompt,
    input_pydantic_model=OrderInput2,
    state_pydantic_model=PaymentOrder,
    tool_registry_or_tool_defs=AIRLINE_TOOL_REGISTRY,
    tool_names=["calculate"],
)


# ------------------------------------------------------------------


class OrderInput3(BaseModel):
    user_details: UserDetails
    reservation_details: ReservationDetails
    flight_infos: List[FlightInfo]
    payment_id: str


class UpdateOrder(BaseStateModel):
    is_change_successfull: bool = False


update_flight_node_schema = NodeSchema(
    node_prompt=PREAMBLE
    + "Right now, you have all the data necessary to place the booking.",
    node_system_prompt=AirlineNodeSystemPrompt,
    input_pydantic_model=OrderInput3,
    state_pydantic_model=UpdateOrder,
    tool_registry_or_tool_defs=AIRLINE_TOOL_REGISTRY,
    tool_names=["update_reservation_flights", "calculate"],
)
#----------------------------------------------

edge_schema_1 = EdgeSchema(
    from_node_schema=get_user_id_node_schema,
    to_node_schema = get_reservation_details_node_schema,
    state_condition_fn= lambda state: state.user_details is not None,
    new_input_fn= lambda state, input: UserInput(user_details=state.user_details)
)


edge_schema_2 = EdgeSchema(
    from_node_schema=get_reservation_details_node_schema,
    to_node_schema = find_flight_node_schema,
    state_condition_fn= lambda state: state.reservation_details is not None,
    new_input_fn= lambda state, input: OrderInput1(user_details=input.user_details, reservation_details=state.reservation_details)
)


edge_schema_3 = EdgeSchema(
    from_node_schema=find_flight_node_schema,
    to_node_schema = get_payment_node_schema,
    state_condition_fn= lambda state: state.flight_infos and len(state.flight_infos) > 0,
    new_input_fn= lambda state, input: OrderInput2(user_details=input.user_details, reservation_details=input.reservation_details, flight_infos = state.flight_infos )
)


edge_schema_4 = EdgeSchema(
    from_node_schema=get_payment_node_schema,
    to_node_schema = update_flight_node_schema,
    state_condition_fn= lambda state: state.payment_id is not None,
    new_input_fn= lambda state, input: OrderInput3(user_details=input.user_details, reservation_details=input.reservation_details, flight_infos = input.flight_infos, payment_id = state.payment_id )
)
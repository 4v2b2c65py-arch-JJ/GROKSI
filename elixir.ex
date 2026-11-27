defmodule Elixir do
  @moduledoc "Prepare elixir per ever pile commandment"

  @commandments [
    "load",
    "route",
    "chant",
    "seal",
    "transit"
  ]

  def prepare(pile \\ 1) do
    pile
    |> add_commandments()
    |> mix()
  end

  defp add_commandments(pile) do
    Enum.map(1..pile, fn n ->
      %{pile: n, commandment: Enum.at(@commandments, rem(n - 1, length(@commandments)))}
    end)
  end

  defp mix(items) do
    %{elixir: items, count: length(items), ready: true}
  end
end
import React from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import ConversationPanel from "../components/ConversationPanel"

describe("ConversationPanel Component", () => {
  const dummyProfile = {
    part: "Brake Pads",
    maker: "Maruti",
    model: "Swift",
    year: "2018",
    variant: "VXi Petrol",
  }

  it("renders empty state placeholder when no messages are provided", () => {
    render(
      <ConversationPanel
        messages={[]}
        pendingQuestion={null}
        vehicleProfile={{}}
        onSendMessage={vi.fn()}
        onReplyQuestion={vi.fn()}
        isSearching={false}
        activeSupplierCount={0}
      />
    )

    expect(screen.getByText("Ready to find automotive parts")).toBeDefined()
  })

  it("renders messages for both bot and mechanic", () => {
    const messages = [
      { role: "agent", text: "Hello! What part do you need?", timestamp: "10:00 AM" },
      { role: "mechanic", text: "I need front brake pads for Maruti Swift.", timestamp: "10:01 AM" },
    ]

    render(
      <ConversationPanel
        messages={messages}
        pendingQuestion={null}
        vehicleProfile={dummyProfile}
        onSendMessage={vi.fn()}
        onReplyQuestion={vi.fn()}
        isSearching={false}
        activeSupplierCount={0}
      />
    )

    expect(screen.getByText("Hello! What part do you need?")).toBeDefined()
    expect(screen.getByText("I need front brake pads for Maruti Swift.")).toBeDefined()
    expect(screen.getByText("Part: Brake Pads")).toBeDefined()
  })

  it("calls onSendMessage when typing and submitting a message", () => {
    const onSendMock = vi.fn()
    render(
      <ConversationPanel
        messages={[]}
        pendingQuestion={null}
        vehicleProfile={{}}
        onSendMessage={onSendMock}
        onReplyQuestion={vi.fn()}
        isSearching={false}
        activeSupplierCount={0}
      />
    )

    const input = screen.getByPlaceholderText(/type part name or car details/i)
    fireEvent.change(input, { target: { value: "Oil filter for Tata Nexon" } })

    const form = input.closest("form")
    fireEvent.submit(form)

    expect(onSendMock).toHaveBeenCalledWith("Oil filter for Tata Nexon")
  })

  it("renders pending question options and triggers onReplyQuestion", () => {
    const onReplyMock = vi.fn()
    const pendingQuestion = {
      question: "Which fuel type is your Swift?",
      options: ["Petrol", "Diesel", "CNG"],
    }

    render(
      <ConversationPanel
        messages={[{ role: "agent", text: "Checking vehicle details" }]}
        pendingQuestion={pendingQuestion}
        vehicleProfile={{ maker: "Maruti", model: "Swift" }}
        onSendMessage={vi.fn()}
        onReplyQuestion={onReplyMock}
        isSearching={false}
        activeSupplierCount={0}
      />
    )

    expect(screen.getByText("Which fuel type is your Swift?")).toBeDefined()
    const petrolBtn = screen.getByRole("button", { name: "Petrol" })
    fireEvent.click(petrolBtn)

    expect(onReplyMock).toHaveBeenCalledWith("Petrol")
  })
})

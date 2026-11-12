import React from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import ProductResults from "../components/ProductResults"

describe("ProductResults Component", () => {
  const sampleSuppliers = [
    { id: "boodmo", vendor: "boodmo", name: "Boodmo", status: "Completed" },
    { id: "autodukan", vendor: "autodukan", name: "AutoDukan", status: "Completed" },
  ]

  const sampleListings = [
    {
      title: "Bosch Front Brake Pads",
      brand: "Bosch",
      part_number: "0986AB1234",
      price: 1200,
      mrp: 1600,
      url: "https://boodmo.com/p/1",
      vendor: "boodmo",
      available: true,
      fitment: "verified",
      relevance: "EXACT_MATCH",
      best_offer: { seller: "SparesHub", dispatch: "0-2 days", stock: "In Stock" },
    },
    {
      title: "Brembo High Performance Brake Pads",
      brand: "Brembo",
      part_number: "P83024",
      price: 2500,
      mrp: 3000,
      url: "https://boodmo.com/p/2",
      vendor: "boodmo",
      available: true,
      fitment: "verified",
      relevance: "EXACT_MATCH",
      best_offer: { seller: "Speedway Spares", dispatch: "Same day", stock: "In Stock" },
    },
    {
      title: "OEM Brake Pad Set",
      brand: "Maruti Genuine",
      part_number: "55810M68P00",
      price: 1450,
      mrp: 1550,
      url: "https://autodukan.com/p/3",
      vendor: "autodukan",
      available: true,
      fitment: "unverified",
      relevance: "EXACT_MATCH",
      best_offer: { seller: "AutoDukan Central", dispatch: "Standard", stock: "In Stock" },
    },
    {
      title: "Brake Caliper Guide Pin Kit",
      brand: "KBX",
      part_number: "KBX-99",
      price: 350,
      mrp: 400,
      url: "https://boodmo.com/p/4",
      vendor: "boodmo",
      available: true,
      fitment: "verified",
      relevance: "COMPONENT",
      best_offer: { seller: "BrakeTech", dispatch: "Standard", stock: "In Stock" },
    },
  ]

  it("renders both supplier sections separately without mixing listings", () => {
    render(
      <ProductResults
        listings={sampleListings}
        suppliers={sampleSuppliers}
        activeFilter="all"
        onSelectFilter={vi.fn()}
      />
    )

    expect(screen.getByText("Boodmo Verified Catalog")).toBeDefined()
    expect(screen.getByText("AutoDukan Verified Catalog")).toBeDefined()
    expect(screen.getByText("Bosch Front Brake Pads")).toBeDefined()
    expect(screen.getByText("OEM Brake Pad Set")).toBeDefined()
  })

  it("calculates exact procurement recommendation and savings", () => {
    render(
      <ProductResults
        listings={sampleListings}
        suppliers={sampleSuppliers}
        activeFilter="all"
        onSelectFilter={vi.fn()}
      />
    )

    // Boodmo cheapest is KBX Guide Pin Kit @ ₹350. AutoDukan is OEM @ ₹1,450.
    // Savings = 1,450 - 350 = ₹1,100.
    expect(screen.getByText(/Source from Boodmo: Save ₹1,100/i)).toBeDefined()
  })

  it("filters listings when search query is typed", () => {
    render(
      <ProductResults
        listings={sampleListings}
        suppliers={sampleSuppliers}
        activeFilter="all"
        onSelectFilter={vi.fn()}
      />
    )

    const searchInput = screen.getByPlaceholderText(/search parts, brands/i)
    fireEvent.change(searchInput, { target: { value: "Brembo" } })

    expect(screen.getByText("Brembo High Performance Brake Pads")).toBeDefined()
    expect(screen.queryByText("Bosch Front Brake Pads")).toBeNull()
  })

  it("filters listings by relevance category", () => {
    render(
      <ProductResults
        listings={sampleListings}
        suppliers={sampleSuppliers}
        activeFilter="all"
        onSelectFilter={vi.fn()}
      />
    )

    // Click on Exact Matches filter button
    const exactButton = screen.getByRole("button", { name: /Exact Matches \(3\)/i })
    fireEvent.click(exactButton)

    expect(screen.getByText("Bosch Front Brake Pads")).toBeDefined()
    expect(screen.queryByText("Brake Caliper Guide Pin Kit")).toBeNull()
  })
})

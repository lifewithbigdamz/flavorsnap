import type { NextApiRequest, NextApiResponse } from "next";

type ClassificationResult = {
  food: string;
  confidence: number;
  calories?: number;
};

type Data = ClassificationResult | { error: string };

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data>,
) {
  // Simulate random errors for testing
  if (Math.random() < 0.3) {
    return res.status(500).json({ error: "Classification service temporarily unavailable" });
  }

  if (Math.random() < 0.2) {
    return res.status(400).json({ error: "Invalid image format" });
  }

  // Simulate processing delay
  setTimeout(() => {
    const foods = ["Pizza", "Burger", "Salad", "Pasta", "Sushi", "Tacos"];
    const randomFood = foods[Math.floor(Math.random() * foods.length)];
    
    const result: ClassificationResult = {
      food: randomFood,
      confidence: Math.random() * 0.3 + 0.7, // 0.7 to 1.0
      calories: Math.floor(Math.random() * 500) + 200,
    };

    res.status(200).json(result);
  }, 1000 + Math.random() * 2000); // 1-3 second delay
}

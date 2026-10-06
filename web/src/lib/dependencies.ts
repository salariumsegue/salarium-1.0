export const dependencyGroups = [
  {
    id: "compute",
    label: "AI & data-center investment",
    thesis:
      "Demand for compute infrastructure may connect networking and data-center businesses. This is a qualitative research hypothesis, not a measured return factor.",
    members: [
      {
        ticker: "CIEN",
        url: "https://www.ciena.com/",
        basis: "Networking systems and cloud / AI connectivity.",
      },
      {
        ticker: "APLD",
        url: "https://www.applieddigital.com/",
        basis: "Data-center infrastructure for high-performance computing.",
      },
    ],
  },
  {
    id: "power",
    label: "Power-intensive infrastructure",
    thesis:
      "Power availability, construction costs, and financing conditions may affect very different businesses. These links do not establish equal sensitivity or return correlation.",
    members: [
      {
        ticker: "APLD",
        url: "https://www.applieddigital.com/",
        basis: "Power-dependent data-center operations.",
      },
      {
        ticker: "MARA",
        url: "https://www.mara.com/",
        basis: "Digital energy and computing operations.",
      },
      {
        ticker: "SMR",
        url: "https://www.nuscalepower.com/",
        basis: "Small modular nuclear reactor technology.",
      },
    ],
  },
] as const;

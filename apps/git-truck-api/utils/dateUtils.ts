const convertUnixTimeToDate = (unixTime: number): Date => {
  return new Date(unixTime * 1000);
};

const formatDate = (date: Date): string => {
  const day = date.getDate();
  const monthIndex = date.getMonth();
  const year = date.getFullYear();

  const monthNames = [
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
  ];

  const monthAbbr = monthNames[monthIndex];
  return `${day} ${monthAbbr} ${year}`;
};

export { convertUnixTimeToDate, formatDate };

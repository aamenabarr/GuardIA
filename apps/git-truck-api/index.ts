import express, { Request, Response } from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import api from './routes';

const app = express();

app.use(cors());

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

app.use("/api", api);
app.get("/", (_: Request, res: Response) => {
  res.status(200).send({ message: "Welcome to the Git-TruckXR API" });
});

app.listen(8080, () => {
  // eslint-disable-next-line no-console
  console.log("El servidor está corriendo en el puerto 8080");
});

export default app;

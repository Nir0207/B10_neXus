import { getConfig } from "./config";
import { createApp } from "./app";
import { connectToMongo, disconnectFromMongo, MongoTelemetryEventRepository, MongoUserRepository } from "./mongo";
import { ensureAdminUser } from "./services";

async function main(): Promise<void> {
  const config = getConfig();

  await connectToMongo(config);
  const userRepository = new MongoUserRepository();
  const telemetryRepository = new MongoTelemetryEventRepository();

  await ensureAdminUser(userRepository, config);

  const { app } = await createApp({
    config,
    telemetryRepository,
    userRepository,
  });

  const server = app.listen(config.port, () => {
    console.log(`BioNexus telemetry GraphQL service listening on port ${config.port}`);
  });

  const shutdown = async (): Promise<void> => {
    await new Promise<void>((resolve: () => void, reject: (error?: Error) => void) => {
      server.close((error?: Error) => {
        if (error) {
          reject(error);
          return;
        }

        resolve();
      });
    });
    await disconnectFromMongo();
  };

  process.on("SIGINT", () => {
    void shutdown().finally(() => process.exit(0));
  });
  process.on("SIGTERM", () => {
    void shutdown().finally(() => process.exit(0));
  });
}

void main().catch((error: unknown) => {
  console.error("Telemetry service failed to start", error);
  process.exit(1);
});

local typedefs = require "kong.db.schema.typedefs"

return {
  name = "chain-plugin",
  fields = {
    { consumer = typedefs.no_consumer },
    { protocols = typedefs.protocols_http },
    { config = {
        type = "record",
        fields = {
          { policy_service = { type = "string", required = true, default = "policy" } },
          { retriever_service = { type = "string", required = true, default = "retriever" } },
            { processor_service = { type = "string", required = true, default = "processor" } },
          { log_path = { type = "string", required = false, default = "/var/log/microservices/audit.jsonl" } },
          { idempotency_ttl = { type = "integer", required = false, default = 300 } },
        },
        entity_checks = {
        }
      }
    }
  }
}

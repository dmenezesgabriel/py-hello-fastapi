iam_policies = {
  "policy-custom" : {
    document = "policy/policy-custom.json"
  }
}

iam_roles = {
  "lambda-role" : {
    trust_policy_document = "role/trust-lambda.json"
    attach_policies       = ["arn:aws:iam::accountnumber:policy/policy-custom"]
  }
}

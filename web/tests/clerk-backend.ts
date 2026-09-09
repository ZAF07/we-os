import { createClerkClient } from "@clerk/nextjs/server";

/**
 * Clerk's Backend API, for the tenantless project's fixture.
 *
 * The tenantless user stops being tenantless the moment a spec succeeds — it
 * has named a business, and Clerk now holds an Organization with that user in
 * it. The project therefore depends on putting the fixture back, and this is
 * how: the same Backend API the sign-in setup already mints tickets with,
 * reached through the Next.js package because that is the one this app
 * depends on directly.
 */

/**
 * Returns a Backend API client for the shared test instance.
 *
 * Returns:
 *   The client, authenticated with the secret key from the environment.
 */
function backend() {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) {
    throw new Error(
      "CLERK_SECRET_KEY is required to manage the tenantless user's " +
        "organizations. See web/.env.local.example.",
    );
  }
  return createClerkClient({ secretKey });
}

/**
 * Finds the Clerk user behind a test email address.
 *
 * Args:
 *   email: The test user's email address.
 *
 * Returns:
 *   The user's id.
 */
async function userIdFor(email: string): Promise<string> {
  const { data } = await backend().users.getUserList({
    emailAddress: [email],
  });
  const user = data[0];
  if (!user) throw new Error(`No Clerk user has the email ${email}.`);
  return user.id;
}

/**
 * Deletes every Organization a test user belongs to.
 *
 * Args:
 *   email: The test user's email address.
 *
 * Returns:
 *   How many Organizations were deleted.
 */
export async function deleteOrganizationsOf(email: string): Promise<number> {
  const clerk = backend();
  const { data: memberships } = await clerk.users.getOrganizationMembershipList(
    {
      userId: await userIdFor(email),
      limit: 100,
    },
  );
  for (const membership of memberships) {
    await clerk.organizations.deleteOrganization(membership.organization.id);
  }
  return memberships.length;
}

/**
 * Creates an Organization with a test user as its admin, around the app.
 *
 * The app never leaves a business without a tier on purpose, so a spec that
 * needs one — to prove Home sends it back to finish — has to build it here.
 *
 * Args:
 *   email: The test user's email address.
 *   name: The Organization's name.
 *
 * Returns:
 *   The new Organization's id.
 */
export async function createOrganizationFor(
  email: string,
  name: string,
): Promise<string> {
  const organization = await backend().organizations.createOrganization({
    name,
    createdBy: await userIdFor(email),
  });
  return organization.id;
}

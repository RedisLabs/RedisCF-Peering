# AWS CloudFormation Project

## Table of Contents
- [Introduction](#introduction)
- [Stack Create](#stack-create)
- [Stack Update](#stack-update)
- [Stack Delete](#stack-delete)
- [Conclusion](#conclusion)

## Introduction
This repository contains an AWS CloudFormation project that simplifies the management of AWS resources using infrastructure as code. With CloudFormation, you can create, update, and delete stacks of AWS resources in a controlled and automated manner.

## Stack Create
The "Stack Create" chapter provides guidance on how to create a new CloudFormation stack. It covers the following topics:
- Prerequisites for creating a stack.
  1. Redis credentials must be configured in AWS Secrets Manager
  2. CloudFormation templates are available in the S3 Bucket together will the Lambda archives and the Layers for Lambda.
- How to define and configure a CloudFormation template.
  1. Login to AWS Console and navigate to CloudFormation.
  2. Go to Stacks, press Create stack and choose With new resources (standard).
  3. Select the template source as Amazon S3 URL and below set the URL from S3 for the desired version. The template for CloudFormation is of type .yml.
  4. Press Next.
  5. In the Specify stack details page complete the fields with the desired values. All the parameters with [Required] tag must have a value.
  6. Press Next.
  7. In the Configure stack options don’t change anything. Just press Next.
  8. On the Review *stack name* page double check that all the parameters have the correct values, then go at the bottom of the page, check I acknowledge that AWS CloudFormation might create IAM resources with     customized names and press Submit.
  9. After that, the stack Creation will begin and all the resources states will be displayed in the Events tab.
- The deployment process of the stack.
  1. The stack begins with the resource creation as defined in the CloudFormation template.
  2. Once the resources are created, the Lambda function is triggered and will create the required resource if no error is raised.


## Stack Update
The "Stack Update" chapter discusses the process of updating an existing CloudFormation stack. It includes information on:
- Modifying existing AWS resources within a stack.
  1. Modifying resources requires an already created stack in a COMPLETE state.
  2. To start an Update action, select that stack and press the Update button.
  3. On the Update stack page check the Use current template box and click Next.
  4. On the Specify stack details change the parameters as desired but only the ones accepted by Swagger as a PUT action. Then press Next.
  5. In the Configuration stack options page just press Next.
  6. In the Review *stack name* page check the I acknowledge that AWS CloudFormation might create IAM resources with customized names button and press Submit.
  7. Check the Events page and wait for the Update to complete.


## Stack Delete
In the "Stack Delete" chapter, we explore the steps involved in deleting a CloudFormation stack. This chapter covers:
- How to initiate the deletion process.
  1. For the Delete action, press the Delete button and confirm that the stack should be permanently deleted.
  2. After all the resources created by CloudFormation template are deleted, in the Events tab the last event must be DELETE_COMPLETE for the resource having the Logical ID the name of the stack.


## Conclusion
This concludes the overview of the AWS CloudFormation project. You can use this repository to manage your Redis infrastructure efficiently and consistently.
